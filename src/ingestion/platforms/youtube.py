"""
YouTube ingester — pulls video metadata and comments.
Owner: Claude

Uses YouTube Data API v3 when key is available.
Falls back to Invidious public API (no key needed).
"""

import os
from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class YouTubeIngester(BaseIngester):
    """Ingest data from YouTube."""

    platform = Platform.YOUTUBE

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()

        if self.api_key:
            return await self._search_youtube_api(query, since, max_results)
        return await self._search_invidious(query, since, max_results)

    async def _search_youtube_api(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Search via YouTube Data API v3."""
        signals = []
        try:
            resp = await self._client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "relevance",
                    "maxResults": min(max_results, 50),
                    "publishedAfter": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            video_ids = []
            video_snippets = {}
            for item in data.get("items", []):
                vid = item["id"].get("videoId")
                if vid:
                    video_ids.append(vid)
                    video_snippets[vid] = item.get("snippet", {})

            # Fetch video statistics in batch
            stats = {}
            if video_ids:
                stats = await self._fetch_video_stats(video_ids)

            for vid in video_ids:
                snippet = video_snippets.get(vid, {})
                video_stats = stats.get(vid, {})

                published = snippet.get("publishedAt")
                ts = None
                if published:
                    try:
                        ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.now()

                title = snippet.get("title", "")
                description = snippet.get("description", "")
                content = f"{title} — {description[:300]}" if description else title

                signals.append(RawSignal(
                    platform=Platform.YOUTUBE,
                    signal_type=SignalType.SOCIAL_POST,
                    content=content,
                    author=snippet.get("channelTitle"),
                    url=f"https://youtube.com/watch?v={vid}",
                    timestamp=ts,
                    engagement={
                        "likes": int(video_stats.get("likeCount", 0)),
                        "comments": int(video_stats.get("commentCount", 0)),
                        "shares": 0,
                    },
                    metadata={
                        "video_id": vid,
                        "channel_id": snippet.get("channelId"),
                        "view_count": int(video_stats.get("viewCount", 0)),
                        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    },
                    raw_data={"snippet": snippet, "stats": video_stats},
                ))

        except Exception as e:
            print(f"[YouTube] API search failed: {e}")

        return signals[:max_results]

    async def _fetch_video_stats(self, video_ids: List[str]) -> dict:
        """Batch fetch video statistics."""
        stats = {}
        try:
            resp = await self._client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(video_ids[:50]),
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                stats[item["id"]] = item.get("statistics", {})
        except Exception as e:
            print(f"[YouTube] Stats fetch failed: {e}")
        return stats

    async def _search_invidious(
        self, query: str, since: datetime, max_results: int
    ) -> List[RawSignal]:
        """Fallback: Invidious public API (no key needed)."""
        signals = []
        instances = [
            "https://vid.puffyan.us",
            "https://invidious.snopyta.org",
            "https://invidious.kavin.rocks",
        ]

        for base_url in instances:
            try:
                resp = await self._client.get(
                    f"{base_url}/api/v1/search",
                    params={
                        "q": query,
                        "type": "video",
                        "sort_by": "relevance",
                    },
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for item in data[:max_results]:
                    if item.get("type") != "video":
                        continue

                    published = item.get("published")
                    ts = datetime.fromtimestamp(published) if published else datetime.now()

                    if ts < since:
                        continue

                    vid = item.get("videoId", "")
                    signals.append(RawSignal(
                        platform=Platform.YOUTUBE,
                        signal_type=SignalType.SOCIAL_POST,
                        content=f"{item.get('title', '')} — {item.get('description', '')[:300]}",
                        author=item.get("author"),
                        url=f"https://youtube.com/watch?v={vid}",
                        timestamp=ts,
                        engagement={
                            "likes": 0,
                            "comments": 0,
                            "shares": 0,
                        },
                        metadata={
                            "video_id": vid,
                            "view_count": item.get("viewCount", 0),
                            "length_seconds": item.get("lengthSeconds", 0),
                        },
                        raw_data=item,
                    ))

                if signals:
                    break

            except Exception:
                continue

        return signals[:max_results]

    async def health_check(self) -> bool:
        if self.api_key:
            try:
                resp = await self._client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet", "q": "test",
                        "maxResults": 1, "key": self.api_key,
                    },
                )
                return resp.status_code == 200
            except Exception:
                return False
        try:
            resp = await self._client.get(
                "https://vid.puffyan.us/api/v1/search",
                params={"q": "test", "type": "video"},
                follow_redirects=True,
            )
            return resp.status_code == 200
        except Exception:
            return False
