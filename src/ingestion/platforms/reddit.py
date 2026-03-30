"""
Reddit ingester — pulls posts and comments from Reddit.
Owner: Claude

Uses ScrapeCreators API when available, falls back to public JSON API.
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class RedditIngester(BaseIngester):
    """Ingest data from Reddit."""

    platform = Platform.REDDIT

    def __init__(self):
        self.api_key = os.getenv("SCRAPECREATORS_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[RawSignal]:
        since = since or self.default_since()
        signals: List[RawSignal] = []

        if self.api_key:
            signals = await self._search_scrapecreators(query, since, max_results)
        else:
            signals = await self._search_public_api(query, since, max_results)

        return signals[:max_results]

    async def _search_scrapecreators(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via ScrapeCreators API (higher quality, rate limited)."""
        try:
            resp = await self._client.get(
                "https://api.scrapecreators.com/v1/reddit/search",
                params={"q": query, "limit": min(max_results, 100), "sort": "relevance"},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            signals = []
            for post in data.get("results", []):
                created = post.get("created_utc")
                ts = datetime.fromtimestamp(created) if created else None

                if ts and ts < since:
                    continue

                signals.append(RawSignal(
                    platform=Platform.REDDIT,
                    signal_type=SignalType.SOCIAL_POST,
                    content=f"{post.get('title', '')} {post.get('selftext', '')}".strip(),
                    author=post.get("author"),
                    url=post.get("url"),
                    timestamp=ts,
                    engagement={
                        "likes": post.get("ups", 0),
                        "comments": post.get("num_comments", 0),
                        "shares": 0,
                    },
                    metadata={
                        "subreddit": post.get("subreddit"),
                        "flair": post.get("link_flair_text"),
                    },
                    raw_data=post,
                ))
            return signals

        except Exception as e:
            print(f"[Reddit] ScrapeCreators failed: {e}, falling back to public API")
            return await self._search_public_api(query, since, max_results)

    async def _search_public_api(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via Reddit public JSON API (no key needed, lower limits)."""
        signals = []
        try:
            resp = await self._client.get(
                "https://www.reddit.com/search.json",
                params={
                    "q": query,
                    "limit": min(max_results, 25),
                    "sort": "relevance",
                    "t": "month",
                },
                headers={"User-Agent": "LiveMirror/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                created = post.get("created_utc")
                ts = datetime.fromtimestamp(created) if created else None

                if ts and ts < since:
                    continue

                signals.append(RawSignal(
                    platform=Platform.REDDIT,
                    signal_type=SignalType.SOCIAL_POST,
                    content=f"{post.get('title', '')} {post.get('selftext', '')}".strip(),
                    author=post.get("author"),
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    timestamp=ts,
                    engagement={
                        "likes": post.get("ups", 0),
                        "comments": post.get("num_comments", 0),
                        "shares": 0,
                    },
                    metadata={
                        "subreddit": post.get("subreddit"),
                        "flair": post.get("link_flair_text"),
                    },
                    raw_data=post,
                ))

        except Exception as e:
            print(f"[Reddit] Public API failed: {e}")

        return signals

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "https://www.reddit.com/r/all.json?limit=1",
                headers={"User-Agent": "LiveMirror/0.1"},
            )
            return resp.status_code == 200
        except Exception:
            return False
