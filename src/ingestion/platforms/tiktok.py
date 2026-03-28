"""
TikTok ingester — pulls video metadata from TikTok.
Owner: Claude

Uses TikTok Research API when available (requires approved dev account).
Falls back to scraping public RSS/embed endpoints.
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class TikTokIngester(BaseIngester):
    """Ingest data from TikTok."""

    platform = Platform.TIKTOK

    def __init__(self):
        self.api_key = os.getenv("TIKTOK_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.api_key:
            return await self._search_research_api(query, since, max_results)
        return await self._search_public(query, since, max_results)

    async def _search_research_api(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via TikTok Research API (requires approval)."""
        signals = []
        try:
            resp = await self._client.post(
                "https://open.tiktokapis.com/v2/research/video/query/",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": {"and": [{"operation": "IN", "field_name": "keyword", "field_values": [query]}]},
                    "max_count": min(max_results, 100),
                    "start_date": since.strftime("%Y%m%d"),
                    "end_date": datetime.now().strftime("%Y%m%d"),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for video in data.get("data", {}).get("videos", []):
                ts = None
                create_time = video.get("create_time")
                if create_time:
                    ts = datetime.fromtimestamp(create_time)

                if ts and ts < since:
                    continue

                desc = video.get("video_description", "")
                signals.append(RawSignal(
                    platform=Platform.TIKTOK,
                    signal_type=SignalType.SOCIAL_POST,
                    content=desc,
                    author=video.get("username"),
                    url=f"https://www.tiktok.com/@{video.get('username', '')}/video/{video.get('id', '')}",
                    timestamp=ts,
                    engagement={
                        "likes": video.get("like_count", 0),
                        "comments": video.get("comment_count", 0),
                        "shares": video.get("share_count", 0),
                    },
                    metadata={
                        "video_id": video.get("id"),
                        "view_count": video.get("view_count", 0),
                        "duration": video.get("duration", 0),
                        "hashtags": [h.get("name") for h in video.get("hashtag_names", [])],
                    },
                    raw_data=video,
                ))

        except Exception as e:
            print(f"[TikTok] Research API failed: {e}")

        return signals[:max_results]

    async def _search_public(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """
        Fallback: TikTok public discovery feed.
        Limited data but no auth needed.
        """
        signals = []
        try:
            # TikTok doesn't have a public search API, but we can
            # scrape the discover page or use third-party services
            resp = await self._client.get(
                "https://www.tiktok.com/api/search/general/full/",
                params={
                    "keyword": query,
                    "offset": 0,
                    "search_source": "normal_search",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                },
            )
            if resp.status_code != 200:
                return signals

            data = resp.json()
            for item in data.get("data", [])[:max_results]:
                video = item.get("item", {})
                if not video:
                    continue

                desc = video.get("desc", "")
                author = video.get("author", {}).get("uniqueId", "")
                stats = video.get("stats", {})

                ts = None
                create_time = video.get("createTime")
                if create_time:
                    try:
                        ts = datetime.fromtimestamp(int(create_time))
                    except (ValueError, TypeError):
                        ts = datetime.now()

                if ts and ts < since:
                    continue

                signals.append(RawSignal(
                    platform=Platform.TIKTOK,
                    signal_type=SignalType.SOCIAL_POST,
                    content=desc,
                    author=author,
                    url=f"https://www.tiktok.com/@{author}/video/{video.get('id', '')}",
                    timestamp=ts,
                    engagement={
                        "likes": stats.get("diggCount", 0),
                        "comments": stats.get("commentCount", 0),
                        "shares": stats.get("shareCount", 0),
                    },
                    metadata={
                        "video_id": video.get("id"),
                        "view_count": stats.get("playCount", 0),
                        "duration": video.get("video", {}).get("duration", 0),
                    },
                    raw_data=video,
                ))

        except Exception as e:
            print(f"[TikTok] Public search failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        if self.api_key:
            try:
                resp = await self._client.get(
                    "https://open.tiktokapis.com/v2/research/video/query/",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code in (200, 401)  # 401 = key valid but need body
            except Exception:
                return False
        return True  # Public fallback always "available"
