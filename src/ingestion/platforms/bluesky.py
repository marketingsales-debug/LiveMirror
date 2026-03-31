"""
Bluesky ingester — pulls posts from the AT Protocol network.
Owner: Claude

Uses the public Bluesky AppView API. No auth needed for search.
"""

from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class BlueskyIngester(BaseIngester):
    """Ingest data from Bluesky via AT Protocol."""

    platform = Platform.BLUESKY
    BASE_URL = "https://api.bsky.app"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
        )

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        since = since or self.default_since()
        # Ensure since is offset-aware
        if since.tzinfo is None:
            from datetime import timezone
            since = since.replace(tzinfo=timezone.utc)
            
        signals = []

        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/xrpc/app.bsky.feed.searchPosts",
                params={
                    "q": query,
                    "limit": min(max_results, 25),
                    "sort": "latest",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for post_wrapper in data.get("posts", []):
                record = post_wrapper.get("record", {})
                author_info = post_wrapper.get("author", {})

                created = record.get("createdAt")
                ts = None
                if created:
                    try:
                        ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except ValueError:
                        ts = datetime.now()

                if ts and ts < since:
                    continue

                text = record.get("text", "")
                if not text:
                    continue

                # Extract engagement
                like_count = post_wrapper.get("likeCount", 0)
                reply_count = post_wrapper.get("replyCount", 0)
                repost_count = post_wrapper.get("repostCount", 0)

                handle = author_info.get("handle", "")
                uri = post_wrapper.get("uri", "")
                # Convert AT URI to web URL
                rkey = uri.split("/")[-1] if "/" in uri else ""
                web_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else None

                signals.append(RawSignal(
                    platform=Platform.BLUESKY,
                    signal_type=SignalType.SOCIAL_POST,
                    content=text,
                    author=author_info.get("displayName") or handle,
                    url=web_url,
                    timestamp=ts,
                    engagement={
                        "likes": like_count,
                        "comments": reply_count,
                        "shares": repost_count,
                    },
                    metadata={
                        "handle": handle,
                        "did": author_info.get("did"),
                        "uri": uri,
                        "labels": [l.get("val") for l in post_wrapper.get("labels", [])],
                    },
                    raw_data=post_wrapper,
                ))

        except Exception as e:
            print(f"[Bluesky] Search failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/xrpc/app.bsky.feed.searchPosts",
                params={"q": "test", "limit": 1},
            )
            return resp.status_code == 200
        except Exception:
            return False
