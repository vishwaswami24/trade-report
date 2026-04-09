from __future__ import annotations

import asyncio
import html
import logging
import re
from xml.etree import ElementTree

import httpx

from app.core.config import Settings
from app.schemas.market import CollectedMarketData, SourceItem
from app.services.sector_profiles import get_sector_profile

logger = logging.getLogger(__name__)


class MarketDataCollector:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def collect(self, sector: str) -> CollectedMarketData:
        queries = [
            f"{sector} sector India market",
            f"{sector} India outlook",
            f"{sector} India investment news",
        ]

        results = await asyncio.gather(
            *(self._fetch_google_news_rss(query) for query in queries),
            return_exceptions=True,
        )

        unique_links: set[str] = set()
        live_sources: list[SourceItem] = []
        warnings: list[str] = []

        for result in results:
            if isinstance(result, Exception):
                logger.warning("News collection failed: %s", result)
                message = "A live news source could not be reached."
                if message not in warnings:
                    warnings.append(message)
                continue

            for item in result:
                if item.link in unique_links:
                    continue
                unique_links.add(item.link)
                live_sources.append(item)

        profile = get_sector_profile(sector)
        context_notes = [
            f"Sector watchlist: {', '.join(profile['watchlist'])}.",
            f"Primary structural drivers: {', '.join(profile['drivers'])}.",
        ]

        if not live_sources:
            message = (
                "No live sources were available at request time, so the report uses sector heuristics as fallback context."
            )
            if message not in warnings:
                warnings.append(message)

        return CollectedMarketData(
            sector=sector,
            live_sources=live_sources[: self.settings.news_results_limit],
            context_notes=context_notes,
            collection_warnings=warnings,
        )

    async def _fetch_google_news_rss(self, query: str) -> list[SourceItem]:
        response = await self.client.get(
            "https://news.google.com/rss/search",
            params={
                "q": query,
                "hl": "en-IN",
                "gl": "IN",
                "ceid": "IN:en",
            },
            headers={"User-Agent": self.settings.user_agent},
        )
        response.raise_for_status()

        root = ElementTree.fromstring(response.text)
        items: list[SourceItem] = []

        for node in root.findall(".//item")[: self.settings.news_results_limit]:
            title = self._clean_text(node.findtext("title"))
            link = self._clean_text(node.findtext("link"))
            snippet = self._strip_html(node.findtext("description") or "")
            source_node = node.find("source")
            published_at = self._clean_text(node.findtext("pubDate"))
            source_name = (
                source_node.text.strip()
                if source_node is not None and source_node.text
                else "Google News"
            )

            if title and link:
                items.append(
                    SourceItem(
                        title=title,
                        link=link,
                        snippet=snippet,
                        source=source_name,
                        published_at=published_at,
                    )
                )

        return items

    @staticmethod
    def _clean_text(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _strip_html(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()
