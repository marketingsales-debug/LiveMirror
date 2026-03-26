"""
Web search ingester — general web search via Brave Search API.
Owner: Claude

Falls back to DuckDuckGo instant answers if no API key.
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class WebSearchIngester(BaseIngester):
    """Ingest data from web search results."""

    platform = Platform.WEB

    def __init__(self):
        self.brave_key = os.getenv("BRAVE_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        if self.brave_key:
            return await self._search_brave(query, max_results)
        return await self._search_duckduckgo(query, max_results)

    async def _search_brave(self, query: str, max_results: int) -> List[RawSignal]:
        """Search via Brave Search API."""
        signals = []
        try:
            resp = await self._client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": min(max_results, 20), "freshness": "pm"},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.brave_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("web", {}).get("results", []):
                signals.append(RawSignal(
                    platform=Platform.WEB,
                    signal_type=SignalType.NEWS_ARTICLE,
                    content=f"{result.get('title', '')} — {result.get('description', '')}",
                    url=result.get("url"),
                    timestamp=datetime.now(),
                    engagement={"likes": 0, "comments": 0, "shares": 0},
                    metadata={
                        "source": result.get("url", "").split("/")[2] if result.get("url") else "",
                        "language": result.get("language"),
                    },
                    raw_data=result,
                ))
        except Exception as e:
            print(f"[WebSearch] Brave failed: {e}")

        return signals

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[RawSignal]:
        """Fallback: DuckDuckGo instant answers (limited but free, no key)."""
        signals = []
        try:
            resp = await self._client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_redirect": 1},
            )
            resp.raise_for_status()
            data = resp.json()

            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    signals.append(RawSignal(
                        platform=Platform.WEB,
                        signal_type=SignalType.NEWS_ARTICLE,
                        content=topic.get("Text", ""),
                        url=topic.get("FirstURL"),
                        timestamp=datetime.now(),
                        engagement={"likes": 0, "comments": 0, "shares": 0},
                        metadata={"source": "duckduckgo_instant"},
                        raw_data=topic,
                    ))
        except Exception as e:
            print(f"[WebSearch] DuckDuckGo failed: {e}")

        return signals

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "https://api.duckduckgo.com/",
                params={"q": "test", "format": "json"},
            )
            return resp.status_code == 200
        except Exception:
            return False
