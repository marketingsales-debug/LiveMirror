"""
Hacker News ingester — pulls stories and comments from HN.
Owner: Claude

Uses the free HN Algolia API. No key needed.
"""

from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class HackerNewsIngester(BaseIngester):
    """Ingest data from Hacker News via Algolia API."""

    platform = Platform.HACKERNEWS
    BASE_URL = "https://hn.algolia.com/api/v1"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[RawSignal]:
        since = since or self.default_since()
        since_ts = int(since.timestamp())

        signals: List[RawSignal] = []
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/search",
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{since_ts}",
                    "hitsPerPage": min(max_results, 50),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for hit in data.get("hits", []):
                ts = hit.get("created_at")
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None

                signals.append(RawSignal(
                    platform=Platform.HACKERNEWS,
                    signal_type=SignalType.SOCIAL_POST,
                    content=hit.get("title", ""),
                    author=hit.get("author"),
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    timestamp=timestamp,
                    engagement={
                        "likes": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                        "shares": 0,
                    },
                    metadata={
                        "hn_id": hit.get("objectID"),
                        "story_url": hit.get("url"),
                    },
                    raw_data=hit,
                ))

        except Exception as e:
            print(f"[HackerNews] Search failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self.BASE_URL}/search?query=test&hitsPerPage=1")
            return resp.status_code == 200
        except Exception:
            return False
