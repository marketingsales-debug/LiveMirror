"""
Twitter/X ingester — pulls tweets via public search.
Owner: Claude

Uses the Twitter/X API v2 when a bearer token is available.
Falls back to Nitter RSS scraping (public, no key needed).
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class TwitterIngester(BaseIngester):
    """Ingest data from Twitter/X."""

    platform = Platform.TWITTER

    def __init__(self):
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 100,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.bearer_token:
            return await self._search_api_v2(query, since, max_results)
        return await self._search_nitter(query, since, max_results)

    async def _search_api_v2(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via Twitter API v2 (requires bearer token)."""
        signals = []
        try:
            # Cap at 100 per request (API limit)
            count = min(max_results, 100)
            resp = await self._client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params={
                    "query": f"{query} -is:retweet lang:en",
                    "max_results": max(10, count),  # API minimum is 10
                    "tweet.fields": "created_at,public_metrics,author_id,lang",
                    "expansions": "author_id",
                    "user.fields": "username,public_metrics",
                },
                headers={"Authorization": f"Bearer {self.bearer_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Build author lookup
            users = {}
            for user in data.get("includes", {}).get("users", []):
                users[user["id"]] = user.get("username", "")

            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                created = tweet.get("created_at")
                ts = (
                    datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if created else None
                )

                if ts and ts < since:
                    continue

                author_id = tweet.get("author_id", "")
                username = users.get(author_id, "")

                signals.append(RawSignal(
                    platform=Platform.TWITTER,
                    signal_type=SignalType.SOCIAL_POST,
                    content=tweet.get("text", ""),
                    author=username,
                    url=f"https://x.com/{username}/status/{tweet['id']}" if username else None,
                    timestamp=ts,
                    engagement={
                        "likes": metrics.get("like_count", 0),
                        "comments": metrics.get("reply_count", 0),
                        "shares": metrics.get("retweet_count", 0) + metrics.get("quote_count", 0),
                    },
                    metadata={
                        "tweet_id": tweet.get("id"),
                        "impression_count": metrics.get("impression_count", 0),
                        "lang": tweet.get("lang"),
                    },
                    raw_data=tweet,
                ))

        except Exception as e:
            print(f"[Twitter] API v2 search failed: {e}")

        return signals[:max_results]

    async def _search_nitter(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """
        Fallback: scrape Nitter RSS feeds (public, no auth).
        Nitter instances may be unreliable — try multiple.
        """
        signals = []
        nitter_instances = [
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]

        for base_url in nitter_instances:
            try:
                resp = await self._client.get(
                    f"{base_url}/search/rss",
                    params={"f": "tweets", "q": query},
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    continue

                # Parse RSS XML for tweet data
                content = resp.text
                signals = self._parse_nitter_rss(content, since, max_results)
                if signals:
                    break

            except Exception:
                continue

        return signals[:max_results]

    def _parse_nitter_rss(
        self, xml_content: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Parse Nitter RSS XML into RawSignals."""
        import re
        signals = []

        # Simple regex-based XML parsing (avoid lxml dependency)
        items = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)

        for item in items[:max_results]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            desc = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
            pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
            creator = re.search(r'<dc:creator>(.*?)</dc:creator>', item)

            text = ""
            if desc:
                # Strip HTML tags from description
                text = re.sub(r'<[^>]+>', '', desc.group(1)).strip()
            elif title:
                text = title.group(1)

            if not text:
                continue

            ts = None
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    ts = parsedate_to_datetime(pub_date.group(1))
                    # Normalize to naive datetime for comparison
                    if ts.tzinfo is not None:
                        ts = ts.replace(tzinfo=None)
                except Exception:
                    ts = datetime.now()

            if ts and ts < since:
                continue

            signals.append(RawSignal(
                platform=Platform.TWITTER,
                signal_type=SignalType.SOCIAL_POST,
                content=text,
                author=creator.group(1) if creator else None,
                url=link.group(1) if link else None,
                timestamp=ts,
                engagement={"likes": 0, "comments": 0, "shares": 0},
                metadata={"source": "nitter_rss"},
                raw_data={"rss_item": item[:500]},
            ))

        return signals

    async def health_check(self) -> bool:
        if self.bearer_token:
            try:
                resp = await self._client.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    params={"query": "test", "max_results": 10},
                    headers={"Authorization": f"Bearer {self.bearer_token}"},
                )
                return resp.status_code == 200
            except Exception:
                return False
        # Check nitter fallback
        try:
            resp = await self._client.get(
                "https://nitter.privacydev.net",
                follow_redirects=True,
            )
            return resp.status_code == 200
        except Exception:
            return False
