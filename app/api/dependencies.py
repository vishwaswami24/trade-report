from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.services.memory_store import fingerprint

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class RequestContext:
    api_key: str
    client_ip: str
    session_id: str
    rate_limit_key: str


async def validate_api_key(
    api_key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if api_key is None or api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return api_key


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_request_context(
    request: Request,
    api_key: str = Depends(validate_api_key),
) -> RequestContext:
    session_id = request.session.get("session_id")
    if session_id is None:
        session_id = str(uuid4())
        request.session["session_id"] = session_id

    client_ip = get_client_ip(request)
    rate_limit_key = f"{fingerprint(api_key)}:{session_id}:{client_ip}"

    return RequestContext(
        api_key=api_key,
        client_ip=client_ip,
        session_id=session_id,
        rate_limit_key=rate_limit_key,
    )
