from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.dependencies import RequestContext, get_request_context
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.analysis import AnalysisService
from app.services.data_collector import MarketDataCollector
from app.services.memory_store import InMemoryRateLimiter, RateLimitExceeded, SessionStore
from app.services.report_builder import ReportBuilder

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

if settings.api_keys == ("demo-trade-key",):
    logger.warning(
        "Using default demo API key. Replace APP_API_KEYS before production deployment."
    )


def normalize_sector_name(sector: str) -> str:
    normalized = " ".join(sector.replace("-", " ").split())
    compact = normalized.replace(" ", "").replace("&", "")
    if len(normalized) < 2 or not compact.isalpha():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sector must contain only letters, spaces, or ampersands.",
        )
    return normalized.lower()


@asynccontextmanager
async def lifespan(app: FastAPI):
    http_client = httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        follow_redirects=True,
    )
    app.state.http_client = http_client
    app.state.collector = MarketDataCollector(http_client, settings)
    app.state.analyzer = AnalysisService(http_client, settings)
    app.state.report_builder = ReportBuilder()
    app.state.session_store = SessionStore()
    app.state.rate_limiter = InMemoryRateLimiter(
        limit=settings.requests_per_minute,
        window_seconds=settings.rate_limit_window_seconds,
    )

    yield

    await http_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "FastAPI service that collects Indian sector market context, analyzes it "
        "with Gemini or a fallback heuristic engine, and returns a markdown report."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.environment == "production",
    max_age=86400,
)


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please retry after the reset window.",
            "retry_after_seconds": exc.reset_in_seconds,
        },
        headers={
            "Retry-After": str(exc.reset_in_seconds),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.reset_in_seconds),
        },
    )


@app.get(
    "/analyze/{sector}",
    response_class=PlainTextResponse,
    summary="Analyze a sector and return a markdown report",
    responses={
        200: {"content": {"text/markdown": {}}},
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "External service unavailable"},
    },
)
async def analyze_sector(
    request: Request,
    sector: str = Path(
        ...,
        min_length=2,
        max_length=40,
        pattern=r"^[A-Za-z][A-Za-z\s&-]{1,39}$",
        description="Sector name such as pharmaceuticals, technology, or agriculture",
    ),
    context: RequestContext = Depends(get_request_context),
) -> PlainTextResponse:
    normalized_sector = normalize_sector_name(sector)

    await request.app.state.session_store.ensure_session(
        session_id=context.session_id,
        client_ip=context.client_ip,
        api_key=context.api_key,
    )

    rate_status = await request.app.state.rate_limiter.consume(context.rate_limit_key)

    try:
        market_data = await request.app.state.collector.collect(normalized_sector)
        analysis = await request.app.state.analyzer.analyze(market_data)
    except httpx.HTTPError as exc:
        logger.exception("External service failed during sector analysis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to reach an external dependency: {exc.__class__.__name__}",
        ) from exc

    session_snapshot = await request.app.state.session_store.record_usage(
        session_id=context.session_id,
        client_ip=context.client_ip,
        api_key=context.api_key,
        sector=normalized_sector,
    )

    markdown_report = request.app.state.report_builder.build(
        sector=normalized_sector,
        market_data=market_data,
        analysis=analysis,
        session_snapshot=session_snapshot,
    )

    return PlainTextResponse(
        markdown_report,
        media_type="text/markdown",
        headers={
            "Cache-Control": "no-store",
            "X-Session-ID": session_snapshot.session_id,
            "X-RateLimit-Limit": str(rate_status.limit),
            "X-RateLimit-Remaining": str(rate_status.remaining),
            "X-RateLimit-Reset": str(rate_status.reset_in_seconds),
        },
    )
