from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque

from app.schemas.market import RateLimitStatus, SessionSnapshot


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


@dataclass
class SessionRecord:
    session_id: str
    client_ip: str
    api_key_fingerprint: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_requests: int = 0
    tracked_sectors: list[str] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = asyncio.Lock()

    async def ensure_session(
        self,
        session_id: str,
        client_ip: str,
        api_key: str,
    ) -> SessionSnapshot:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                record = SessionRecord(
                    session_id=session_id,
                    client_ip=client_ip,
                    api_key_fingerprint=fingerprint(api_key),
                )
                self._sessions[session_id] = record

            return SessionSnapshot(
                session_id=record.session_id,
                created_at=record.created_at,
                total_requests=record.total_requests,
                tracked_sectors=list(record.tracked_sectors),
            )

    async def record_usage(
        self,
        session_id: str,
        client_ip: str,
        api_key: str,
        sector: str,
    ) -> SessionSnapshot:
        async with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                record = SessionRecord(
                    session_id=session_id,
                    client_ip=client_ip,
                    api_key_fingerprint=fingerprint(api_key),
                )
                self._sessions[session_id] = record

            record.total_requests += 1
            if sector not in record.tracked_sectors:
                record.tracked_sectors.append(sector)

            return SessionSnapshot(
                session_id=record.session_id,
                created_at=record.created_at,
                total_requests=record.total_requests,
                tracked_sectors=list(record.tracked_sectors),
            )


class RateLimitExceeded(Exception):
    def __init__(self, *, limit: int, reset_in_seconds: int) -> None:
        self.limit = limit
        self.reset_in_seconds = reset_in_seconds
        super().__init__("Rate limit exceeded")


class InMemoryRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str) -> RateLimitStatus:
        async with self._lock:
            now = time.monotonic()
            bucket = self._requests.setdefault(key, deque())

            while bucket and now - bucket[0] >= self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.limit:
                reset_in_seconds = max(
                    1,
                    math.ceil(self.window_seconds - (now - bucket[0])),
                )
                raise RateLimitExceeded(
                    limit=self.limit,
                    reset_in_seconds=reset_in_seconds,
                )

            bucket.append(now)
            oldest = bucket[0]
            reset_in_seconds = max(
                1,
                math.ceil(self.window_seconds - (now - oldest)),
            )

            return RateLimitStatus(
                limit=self.limit,
                remaining=max(0, self.limit - len(bucket)),
                reset_in_seconds=reset_in_seconds,
            )
