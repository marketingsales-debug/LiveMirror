"""
Instagram ingester — pulls posts via Instagram Graph API.
Owner: Claude

Uses Instagram Graph API (requires Facebook app token).
Falls back to scraping public profile JSON endpoints.
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class InstagramIngester(BaseIngester):
    """Ingest data from Instagram."""

    platform = Platform.INSTAGRAM

    def __init__(self):
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.access_token:
            return await self._search_graph_api(query, since, max_results)
        return await self._search_hashtag_public(query, since, max_results)

    async def _search_graph_api(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via Instagram Graph API (hashtag search)."""
        signals = []
        try:
            # Step 1: Get hashtag ID
            tag = query.replace(" ", "").lower()
            resp = await self._client.get(
                "https://graph.facebook.com/v19.0/ig_hashtag_search",
                params={
                    "q": tag,
                    "access_token": self.access_token,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            hashtag_data = data.get("data", [])
            if not hashtag_data:
                return signals

            hashtag_id = hashtag_data[0].get("id")

            # Step 2: Get recent media for hashtag
            resp = await self._client.get(
                f"https://graph.facebook.com/v19.0/{hashtag_id}/recent_media",
                params={
                    "fields": "id,caption,like_count,comments_count,timestamp,permalink,media_type",
                    "limit": min(max_results, 50),
                    "access_token": self.access_token,
                },
            )
            resp.raise_for_status()
            media_data = resp.json()

            for post in media_data.get("data", []):
                ts = None
                timestamp_str = post.get("timestamp")
                if timestamp_str:
                    try:
                        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if ts.tzinfo:
                            ts = ts.replace(tzinfo=None)
                    except ValueError:
                        ts = datetime.now()

                if ts and ts < since:
                    continue

                caption = post.get("caption", "")
                if not caption:
                    continue

                signals.append(RawSignal(
                    platform=Platform.INSTAGRAM,
                    signal_type=SignalType.SOCIAL_POST,
                    content=caption,
                    url=post.get("permalink"),
                    timestamp=ts,
                    engagement={
                        "likes": post.get("like_count", 0),
                        "comments": post.get("comments_count", 0),
                        "shares": 0,
                    },
                    metadata={
                        "post_id": post.get("id"),
                        "media_type": post.get("media_type"),
                        "hashtag": tag,
                    },
                    raw_data=post,
                ))

        except Exception as e:
            print(f"[Instagram] Graph API failed: {e}")

        return signals[:max_results]

    async def _search_hashtag_public(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """
        Fallback: Scrape public Instagram hashtag page JSON.
        Instagram aggressively blocks scrapers, so this is unreliable.
        """
        signals = []
        tag = query.replace(" ", "").lower()
        try:
            resp = await self._client.get(
                f"https://www.instagram.com/explore/tags/{tag}/",
                params={"__a": "1", "__d": "dis"},
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                return signals

            data = resp.json()
            edges = (
                data.get("graphql", {})
                .get("hashtag", {})
                .get("edge_hashtag_to_media", {})
                .get("edges", [])
            )

            for edge in edges[:max_results]:
                node = edge.get("node", {})
                caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                caption = caption_edges[0].get("node", {}).get("text", "") if caption_edges else ""

                if not caption:
                    continue

                ts = None
                taken_at = node.get("taken_at_timestamp")
                if taken_at:
                    ts = datetime.fromtimestamp(taken_at)

                if ts and ts < since:
                    continue

                shortcode = node.get("shortcode", "")
                signals.append(RawSignal(
                    platform=Platform.INSTAGRAM,
                    signal_type=SignalType.SOCIAL_POST,
                    content=caption,
                    url=f"https://www.instagram.com/p/{shortcode}/" if shortcode else None,
                    timestamp=ts,
                    engagement={
                        "likes": node.get("edge_liked_by", {}).get("count", 0),
                        "comments": node.get("edge_media_to_comment", {}).get("count", 0),
                        "shares": 0,
                    },
                    metadata={
                        "shortcode": shortcode,
                        "is_video": node.get("is_video", False),
                        "hashtag": tag,
                    },
                    raw_data=node,
                ))

        except Exception as e:
            print(f"[Instagram] Public scrape failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        if self.access_token:
            try:
                resp = await self._client.get(
                    "https://graph.facebook.com/v19.0/me",
                    params={"access_token": self.access_token},
                )
                return resp.status_code == 200
            except Exception:
                return False
        return True
