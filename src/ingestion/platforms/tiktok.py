"""
TikTok ingester — pulls video metadata from TikTok.
Owner: Claude

Uses TikTok Research API when available.
Falls back to David Teather's TikTok-Api (Playwright-based).
"""

import os
import asyncio
from typing import List, Optional
from datetime import datetime

import httpx
try:
    from TikTokApi import TikTokApi
    _HAS_TIKTOK_API = True
except ImportError:
    _HAS_TIKTOK_API = False

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class TikTokIngester(BaseIngester):
    """Ingest data from TikTok."""

    platform = Platform.TIKTOK

    def __init__(self):
        self.api_key = os.getenv("TIKTOK_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._ms_token = os.getenv("TIKTOK_MS_TOKEN")

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.api_key:
            research_signals = await self._search_research_api(query, since, max_results)
            if research_signals:
                return research_signals
        
        # Robust fallback using David Teather's library
        if _HAS_TIKTOK_API:
            return await self._search_via_library(query, since, max_results)
            
        return await self._search_public_fallback(query, since, max_results)

    async def _search_via_library(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search using the unofficial TikTok-Api wrapper."""
        signals = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(ms_tokens=[self._ms_token], num_sessions=1, sleep_after=3)
                
                # Fetch trending or searched videos
                results = api.search.videos(query, count=max_results)
                
                async for video in results:
                    v_dict = video.as_dict
                    ts = datetime.fromtimestamp(v_dict.get("createTime", 0))
                    
                    if ts < since:
                        continue

                    author = v_dict.get("author", {}).get("uniqueId", "unknown")
                    stats = v_dict.get("stats", {})

                    signals.append(RawSignal(
                        platform=Platform.TIKTOK,
                        signal_type=SignalType.SOCIAL_POST,
                        content=v_dict.get("desc", ""),
                        author=author,
                        url=f"https://www.tiktok.com/@{author}/video/{v_dict.get('id')}",
                        timestamp=ts,
                        engagement={
                            "likes": stats.get("diggCount", 0),
                            "comments": stats.get("commentCount", 0),
                            "shares": stats.get("shareCount", 0),
                        },
                        metadata={
                            "video_id": v_dict.get("id"),
                            "view_count": stats.get("playCount", 0),
                            "duration": v_dict.get("video", {}).get("duration", 0),
                        },
                        raw_data=v_dict,
                    ))
        except Exception as e:
            print(f"[TikTok] Library search failed: {e}")
            
        return signals

    async def _search_research_api(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via TikTok Research API."""
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
            if resp.status_code == 200:
                data = resp.json()
                for video in data.get("data", {}).get("videos", []):
                    ts = datetime.fromtimestamp(video.get("create_time", 0))
                    if ts < since: continue
                    
                    signals.append(RawSignal(
                        platform=Platform.TIKTOK,
                        signal_type=SignalType.SOCIAL_POST,
                        content=video.get("video_description", ""),
                        author=video.get("username"),
                        url=f"https://www.tiktok.com/@{video.get('username')}/video/{video.get('id')}",
                        timestamp=ts,
                        engagement={
                            "likes": video.get("like_count", 0),
                            "comments": video.get("comment_count", 0),
                            "shares": video.get("share_count", 0),
                        },
                        metadata={"video_id": video.get("id")},
                        raw_data=video,
                    ))
        except Exception as e:
            print(f"[TikTok] Research API failed: {e}")
        return signals

    async def _search_public_fallback(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Generic fallback for public discovery."""
        # Previous scraping logic here...
        return []

    async def health_check(self) -> bool:
        if self.api_key:
            try:
                resp = await self._client.get("https://open.tiktokapis.com/v2/research/video/query/",
                    headers={"Authorization": f"Bearer {self.api_key}"})
                return resp.status_code in (200, 401)
            except Exception: return False
        return _HAS_TIKTOK_API
