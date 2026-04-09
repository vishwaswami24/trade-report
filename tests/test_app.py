from fastapi.testclient import TestClient

from app.main import app
from app.schemas.market import AnalysisResult, CollectedMarketData, SourceItem, TradeOpportunity


def test_missing_api_key_is_rejected():
    with TestClient(app) as client:
        response = client.get("/analyze/pharmaceuticals")
    assert response.status_code == 401


def test_markdown_report_is_returned_for_valid_request():
    class StubCollector:
        async def collect(self, sector: str) -> CollectedMarketData:
            return CollectedMarketData(
                sector=sector,
                live_sources=[
                    SourceItem(
                        title="Indian pharma exports remain strong",
                        link="https://example.com/pharma",
                        snippet="Demand remains healthy across regulated markets.",
                        source="Example News",
                        published_at="Thu, 09 Apr 2026 09:00:00 GMT",
                    )
                ],
                context_notes=["Sector watchlist: Sun Pharma, Cipla."],
                collection_warnings=[],
            )

    class StubAnalyzer:
        async def analyze(self, market_data: CollectedMarketData) -> AnalysisResult:
            return AnalysisResult(
                sector_summary="Pharmaceuticals remain constructive with export and domestic demand support.",
                market_sentiment="Bullish",
                opportunity_score=72,
                key_drivers=["Export demand", "Regulatory approvals", "Domestic prescription growth"],
                trade_opportunities=[
                    TradeOpportunity(
                        title="Momentum trade in leaders",
                        rationale="Leaders are seeing supportive flows.",
                        time_horizon="1-4 weeks",
                        risk_level="Medium",
                    )
                ],
                risk_factors=["Regulatory setbacks"],
                recommended_watchlist=["Sun Pharma", "Cipla"],
            )

    with TestClient(app) as client:
        client.app.state.collector = StubCollector()
        client.app.state.analyzer = StubAnalyzer()

        response = client.get(
            "/analyze/pharmaceuticals",
            headers={"X-API-Key": "demo-trade-key"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# India Sector Trade Opportunity Report: Pharmaceuticals" in response.text
    assert "## Trade Opportunities" in response.text
