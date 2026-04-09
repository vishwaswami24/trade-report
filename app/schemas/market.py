from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    title: str
    link: str
    snippet: str = ""
    source: str
    published_at: str | None = None


class CollectedMarketData(BaseModel):
    sector: str
    live_sources: list[SourceItem] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    collection_warnings: list[str] = Field(default_factory=list)


class TradeOpportunity(BaseModel):
    title: str
    rationale: str
    time_horizon: str
    risk_level: str


class AnalysisResult(BaseModel):
    sector_summary: str
    market_sentiment: str
    opportunity_score: int = Field(ge=0, le=100)
    key_drivers: list[str] = Field(default_factory=list)
    trade_opportunities: list[TradeOpportunity] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    recommended_watchlist: list[str] = Field(default_factory=list)
    scenario: str = "base"
    disclaimer: str = "This report is for educational use only and is not investment advice."


class SessionSnapshot(BaseModel):
    session_id: str
    created_at: datetime
    total_requests: int
    tracked_sectors: list[str] = Field(default_factory=list)


class RateLimitStatus(BaseModel):
    limit: int
    remaining: int
    reset_in_seconds: int
