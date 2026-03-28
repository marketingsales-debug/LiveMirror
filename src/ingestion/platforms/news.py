"""
News ingester — pulls articles from news aggregators.
Owner: Claude

Uses NewsAPI.org when key is available.
Falls back to GNews public API (free, no key, limited).
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class NewsIngester(BaseIngester):
    """Ingest news articles from multiple aggregators."""

    platform = Platform.NEWS

    def __init__(self):
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.newsapi_key:
            return await self._search_newsapi(query, since, max_results)
        return await self._search_gnews(query, since, max_results)

    async def _search_newsapi(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via NewsAPI.org (paid, comprehensive)."""
        signals = []
        try:
            resp = await self._client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": since.strftime("%Y-%m-%d"),
                    "sortBy": "relevancy",
                    "pageSize": min(max_results, 100),
                    "language": "en",
                    "apiKey": self.newsapi_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("articles", []):
                published = article.get("publishedAt")
                ts = None
                if published:
                    try:
                        ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.now()

                title = article.get("title", "")
                description = article.get("description", "")
                content = f"{title} — {description}" if description else title

                signals.append(RawSignal(
                    platform=Platform.NEWS,
                    signal_type=SignalType.NEWS_ARTICLE,
                    content=content,
                    author=article.get("author"),
                    url=article.get("url"),
                    timestamp=ts,
                    engagement={"likes": 0, "comments": 0, "shares": 0},
                    metadata={
                        "source": article.get("source", {}).get("name"),
                        "source_id": article.get("source", {}).get("id"),
                        "image_url": article.get("urlToImage"),
                    },
                    raw_data=article,
                ))

        except Exception as e:
            print(f"[News] NewsAPI failed: {e}")

        return signals[:max_results]

    async def _search_gnews(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Fallback: GNews public API (free, limited to 10 results)."""
        signals = []
        try:
            resp = await self._client.get(
                "https://gnews.io/api/v4/search",
                params={
                    "q": query,
                    "lang": "en",
                    "max": min(max_results, 10),
                    "from": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            # GNews free tier might not work without a key — try anyway
            if resp.status_code != 200:
                return signals

            data = resp.json()
            for article in data.get("articles", []):
                published = article.get("publishedAt")
                ts = None
                if published:
                    try:
                        ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.now()

                title = article.get("title", "")
                description = article.get("description", "")

                signals.append(RawSignal(
                    platform=Platform.NEWS,
                    signal_type=SignalType.NEWS_ARTICLE,
                    content=f"{title} — {description}" if description else title,
                    author=None,
                    url=article.get("url"),
                    timestamp=ts,
                    engagement={"likes": 0, "comments": 0, "shares": 0},
                    metadata={
                        "source": article.get("source", {}).get("name"),
                        "image_url": article.get("image"),
                    },
                    raw_data=article,
                ))

        except Exception as e:
            print(f"[News] GNews failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        if self.newsapi_key:
            try:
                resp = await self._client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"country": "us", "pageSize": 1, "apiKey": self.newsapi_key},
                )
                return resp.status_code == 200
            except Exception:
                return False
        return True  # GNews fallback doesn't have a good health endpoint
