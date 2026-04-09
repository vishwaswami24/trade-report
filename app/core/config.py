from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    api_keys: tuple[str, ...]
    session_secret: str
    gemini_api_key: str | None
    gemini_model: str
    requests_per_minute: int
    rate_limit_window_seconds: int
    http_timeout_seconds: float
    news_results_limit: int
    user_agent: str


@lru_cache
def get_settings() -> Settings:
    raw_api_keys = os.getenv("APP_API_KEYS", "demo-trade-key")
    api_keys = tuple(key.strip() for key in raw_api_keys.split(",") if key.strip())

    return Settings(
        app_name="Trade Opportunity Analyzer",
        environment=os.getenv("APP_ENV", "development").lower(),
        api_keys=api_keys or ("demo-trade-key",),
        session_secret=os.getenv("SESSION_SECRET", secrets.token_urlsafe(32)),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        requests_per_minute=_int_env("REQUESTS_PER_MINUTE", 5),
        rate_limit_window_seconds=_int_env("RATE_LIMIT_WINDOW_SECONDS", 60),
        http_timeout_seconds=_float_env("HTTP_TIMEOUT_SECONDS", 12.0),
        news_results_limit=_int_env("NEWS_RESULTS_LIMIT", 6),
        user_agent="TradeOpportunityAnalyzer/1.0 (+https://fastapi.tiangolo.com)",
    )
