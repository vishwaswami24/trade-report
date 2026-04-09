from __future__ import annotations

import json
import logging
import re

import httpx

from app.core.config import Settings
from app.schemas.market import AnalysisResult, CollectedMarketData, TradeOpportunity
from app.services.sector_profiles import get_sector_profile

logger = logging.getLogger(__name__)

POSITIVE_MARKERS = {
    "growth",
    "expansion",
    "approval",
    "orders",
    "deal",
    "strong",
    "surge",
    "upbeat",
    "investment",
    "demand",
    "profit",
    "record",
}

NEGATIVE_MARKERS = {
    "delay",
    "fall",
    "weak",
    "pressure",
    "decline",
    "risk",
    "cut",
    "volatile",
    "slowdown",
    "drop",
    "loss",
    "warning",
}

THEME_MAP = {
    "approval": "Regulatory approvals and compliance updates",
    "export": "Export demand and currency sensitivity",
    "deal": "Large deal wins and order-book expansion",
    "capex": "Capex pipeline and capacity expansion",
    "demand": "Domestic demand resilience and pricing power",
    "ai": "AI-led technology spending and transformation budgets",
    "monsoon": "Monsoon progress and rural demand support",
    "inflation": "Input-cost inflation and margin management",
    "policy": "Government policy, incentives, and regulatory actions",
}


class AnalysisService:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def analyze(self, market_data: CollectedMarketData) -> AnalysisResult:
        if self.settings.gemini_api_key:
            llm_result = await self._analyze_with_gemini(market_data)
            if llm_result is not None:
                return llm_result

        return self._build_fallback_analysis(market_data)

    async def _analyze_with_gemini(
        self,
        market_data: CollectedMarketData,
    ) -> AnalysisResult | None:
        prompt = self._build_prompt(market_data)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = await self.client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent",
                json=payload,
                headers={
                    "User-Agent": self.settings.user_agent,
                    "x-goog-api-key": self.settings.gemini_api_key,
                },
            )
            response.raise_for_status()
            body = response.json()
            text = (
                body["candidates"][0]["content"]["parts"][0]["text"]
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            parsed = json.loads(text)
            fallback = self._build_fallback_analysis(market_data)
            watchlist = parsed.get("recommended_watchlist") or get_sector_profile(
                market_data.sector
            )["watchlist"]
            trade_opportunities = [
                TradeOpportunity(**opportunity)
                for opportunity in parsed.get("trade_opportunities", [])[:3]
            ] or fallback.trade_opportunities

            return AnalysisResult(
                sector_summary=parsed.get("sector_summary", fallback.sector_summary),
                market_sentiment=parsed.get(
                    "market_sentiment",
                    fallback.market_sentiment,
                ).title(),
                opportunity_score=int(
                    parsed.get("opportunity_score", fallback.opportunity_score)
                ),
                key_drivers=list(parsed.get("key_drivers", []))[:5] or fallback.key_drivers,
                trade_opportunities=trade_opportunities,
                risk_factors=list(parsed.get("risk_factors", []))[:5] or fallback.risk_factors,
                recommended_watchlist=list(watchlist)[:5] or fallback.recommended_watchlist,
                scenario=parsed.get("scenario", "base"),
                disclaimer=parsed.get(
                    "disclaimer",
                    "AI-generated summary based on current market snippets and should be reviewed before making decisions.",
                ),
            )
        except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Gemini analysis failed, switching to fallback mode: %s", exc)
            return None

    def _build_fallback_analysis(
        self,
        market_data: CollectedMarketData,
    ) -> AnalysisResult:
        profile = get_sector_profile(market_data.sector)
        corpus = " ".join(
            [item.title + " " + item.snippet for item in market_data.live_sources]
        ).lower()

        positive_hits = sum(1 for marker in POSITIVE_MARKERS if marker in corpus)
        negative_hits = sum(1 for marker in NEGATIVE_MARKERS if marker in corpus)

        score = 55 + (positive_hits * 4) - (negative_hits * 5)
        if not market_data.live_sources:
            score = 52
        score = max(20, min(85, score))

        if score >= 65:
            sentiment = "Bullish"
        elif score <= 45:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        extracted_drivers = [
            theme
            for keyword, theme in THEME_MAP.items()
            if re.search(rf"\b{re.escape(keyword)}\b", corpus)
        ]
        key_drivers = (extracted_drivers + profile["drivers"])[:4]

        risk_factors = list(profile["risks"])
        if negative_hits:
            risk_factors.insert(
                0,
                "Recent negative or cautious headlines suggest traders should respect stop-loss levels.",
            )

        summary = self._build_summary(
            sector=market_data.sector,
            sentiment=sentiment,
            score=score,
            has_live_sources=bool(market_data.live_sources),
        )

        opportunities = self._build_trade_opportunities(
            sector=market_data.sector,
            sentiment=sentiment,
            drivers=key_drivers,
        )

        return AnalysisResult(
            sector_summary=summary,
            market_sentiment=sentiment,
            opportunity_score=score,
            key_drivers=key_drivers,
            trade_opportunities=opportunities,
            risk_factors=risk_factors[:4],
            recommended_watchlist=profile["watchlist"][:5],
            scenario="base",
            disclaimer=(
                "Fallback analysis was used because Gemini is not configured or an external AI call failed."
            ),
        )

    def _build_prompt(self, market_data: CollectedMarketData) -> str:
        sources = "\n".join(
            f"- {item.title} | {item.source} | {item.published_at or 'Unknown date'} | {item.link}\n  Snippet: {item.snippet}"
            for item in market_data.live_sources
        )
        if not sources:
            sources = "- No live sources were available for this request."

        profile = get_sector_profile(market_data.sector)
        return f"""
You are a market analyst focused on Indian sectors.
Analyze the sector "{market_data.sector}" and return JSON only.

Use these structural watchlist names if live data is thin: {", ".join(profile["watchlist"])}.
Known structural drivers: {", ".join(profile["drivers"])}.
Known structural risks: {", ".join(profile["risks"])}.

Live market snippets:
{sources}

Return valid JSON with this exact shape:
{{
  "sector_summary": "2-3 sentence overview of the sector setup in India",
  "market_sentiment": "Bullish or Neutral or Bearish",
  "opportunity_score": 0,
  "key_drivers": ["driver 1", "driver 2", "driver 3"],
  "trade_opportunities": [
    {{
      "title": "short opportunity name",
      "rationale": "why this trade setup exists",
      "time_horizon": "e.g. 1-4 weeks",
      "risk_level": "Low or Medium or High"
    }}
  ],
  "risk_factors": ["risk 1", "risk 2", "risk 3"],
  "recommended_watchlist": ["company 1", "company 2", "company 3"],
  "scenario": "base or upside or downside",
  "disclaimer": "brief non-advisory disclaimer"
}}
""".strip()

    @staticmethod
    def _build_summary(
        *,
        sector: str,
        sentiment: str,
        score: int,
        has_live_sources: bool,
    ) -> str:
        source_phrase = (
            "Current news flow adds near-term context"
            if has_live_sources
            else "This view leans on sector heuristics because live news was unavailable"
        )
        return (
            f"The Indian {sector} sector currently screens as {sentiment.lower()} with an opportunity score of {score}/100. "
            f"{source_phrase}, and the setup is best approached through liquid leaders plus catalyst-driven swing trades rather than blind sector-wide exposure."
        )

    @staticmethod
    def _build_trade_opportunities(
        *,
        sector: str,
        sentiment: str,
        drivers: list[str],
    ) -> list[TradeOpportunity]:
        primary_driver = drivers[0] if drivers else f"{sector.title()} demand trends"
        secondary_driver = drivers[1] if len(drivers) > 1 else "policy and earnings catalysts"

        if sentiment == "Bullish":
            return [
                TradeOpportunity(
                    title=f"Momentum trade in {sector.title()} leaders",
                    rationale=f"Positive sector tone and {primary_driver.lower()} support breakout or pullback-entry trades in liquid names.",
                    time_horizon="1-4 weeks",
                    risk_level="Medium",
                ),
                TradeOpportunity(
                    title="Catalyst-driven earnings positioning",
                    rationale=f"Upcoming results, guidance updates, and {secondary_driver.lower()} can create re-rating opportunities.",
                    time_horizon="2-6 weeks",
                    risk_level="Medium",
                ),
                TradeOpportunity(
                    title="Ancillary basket participation",
                    rationale="When sector sentiment improves, suppliers and mid-cap enablers often outperform after leaders confirm the trend.",
                    time_horizon="2-8 weeks",
                    risk_level="High",
                ),
            ]

        if sentiment == "Bearish":
            return [
                TradeOpportunity(
                    title=f"Defensive focus inside {sector.title()}",
                    rationale="If participation weakens, traders should prefer cash-generative leaders and avoid leveraged lower-quality names.",
                    time_horizon="1-3 weeks",
                    risk_level="Low",
                ),
                TradeOpportunity(
                    title="Hedge or reduce aggressive long exposure",
                    rationale=f"Uncertain momentum and {secondary_driver.lower()} argue for smaller position sizing until strength returns.",
                    time_horizon="Immediate to 2 weeks",
                    risk_level="Medium",
                ),
                TradeOpportunity(
                    title="Wait for confirmed reversal setup",
                    rationale="A contrarian entry is higher quality only after support holds and volume confirms stabilization.",
                    time_horizon="Trigger-based",
                    risk_level="High",
                ),
            ]

        return [
            TradeOpportunity(
                title="Range-bound swing trade with catalyst watch",
                rationale=f"Mixed sentiment suggests taking tactical entries around support and resistance while tracking {primary_driver.lower()}.",
                time_horizon="1-3 weeks",
                risk_level="Medium",
            ),
            TradeOpportunity(
                title="Relative-strength basket",
                rationale="Favor leaders holding earnings quality and delivery momentum while avoiding weak laggards inside the same sector.",
                time_horizon="2-5 weeks",
                risk_level="Medium",
            ),
            TradeOpportunity(
                title="Event-driven breakout confirmation",
                rationale=f"A clear policy, demand, or earnings trigger tied to {secondary_driver.lower()} can move the sector out of consolidation.",
                time_horizon="Trigger-based",
                risk_level="High",
            ),
        ]
