from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.market import AnalysisResult, CollectedMarketData, SessionSnapshot


class ReportBuilder:
    def build(
        self,
        *,
        sector: str,
        market_data: CollectedMarketData,
        analysis: AnalysisResult,
        session_snapshot: SessionSnapshot,
    ) -> str:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"# India Sector Trade Opportunity Report: {sector.title()}",
            "",
            "## Request Metadata",
            f"- Generated At: {generated_at}",
            f"- Session ID: `{session_snapshot.session_id}`",
            f"- Requests In Session: {session_snapshot.total_requests}",
            f"- Scenario: {analysis.scenario.title()}",
            "",
            "## Executive Summary",
            analysis.sector_summary,
            "",
            f"**Market Sentiment:** {analysis.market_sentiment}",
            "",
            f"**Opportunity Score:** {analysis.opportunity_score}/100",
            "",
            "## Key Drivers",
        ]

        lines.extend(f"- {driver}" for driver in analysis.key_drivers)

        lines.extend(["", "## Trade Opportunities"])
        for index, opportunity in enumerate(analysis.trade_opportunities, start=1):
            lines.extend(
                [
                    f"### {index}. {opportunity.title}",
                    f"- Rationale: {opportunity.rationale}",
                    f"- Time Horizon: {opportunity.time_horizon}",
                    f"- Risk Level: {opportunity.risk_level}",
                    "",
                ]
            )

        lines.append("## Risk Factors")
        lines.extend(f"- {risk}" for risk in analysis.risk_factors)

        lines.extend(["", "## Watchlist"])
        lines.extend(f"- {item}" for item in analysis.recommended_watchlist)

        lines.extend(["", "## Data Collection Notes"])
        if market_data.collection_warnings:
            lines.extend(f"- {warning}" for warning in market_data.collection_warnings)
        else:
            lines.append("- Live market snippets were collected successfully.")

        lines.extend(f"- {note}" for note in market_data.context_notes)

        lines.extend(["", "## Sources"])
        if market_data.live_sources:
            for item in market_data.live_sources:
                lines.append(
                    f"- [{item.title}]({item.link}) | {item.source} | {item.published_at or 'Unknown date'}"
                )
        else:
            lines.append("- Live source links were unavailable for this request.")

        lines.extend(
            [
                "",
                "## Disclaimer",
                analysis.disclaimer,
            ]
        )

        return "\n".join(lines).strip() + "\n"
