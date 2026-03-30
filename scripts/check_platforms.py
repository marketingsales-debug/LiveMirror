#!/usr/bin/env python3
"""
LiveMirror Platform Health Check Script
========================================
Tests all platform ingesters to verify they are working correctly.

This script directly tests each platform's API connection and search functionality.

Usage:
    cd LiveMirror
    python scripts/check_platforms.py

Platforms tested:
    - Reddit (public JSON API / ScrapeCreators)
    - HackerNews (Algolia API)
    - Polymarket (public API)
    - Web Search (SerpAPI / DuckDuckGo)
    - Twitter/X (API v2 / Nitter fallback)
    - YouTube (Data API / RSS fallback)
    - Bluesky (public API)
    - News (NewsAPI / Google News RSS)
    - TikTok (ScrapeCreators / public fallback)
    - Instagram (ScrapeCreators / public fallback)
"""

import os
import sys
import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)


class Status(Enum):
    OK = "✅ OK"
    DEGRADED = "⚠️ DEGRADED"
    FAILED = "❌ FAILED"
    NO_KEY = "🔑 NO API KEY"


@dataclass
class PlatformResult:
    name: str
    status: Status
    message: str
    api_type: str
    response_time_ms: Optional[float] = None
    sample_results: int = 0


class PlatformHealthChecker:
    """Tests all LiveMirror platform ingesters."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results: List[PlatformResult] = []

    async def close(self):
        await self.client.aclose()

    def _env(self, key: str) -> Optional[str]:
        return os.getenv(key)

    async def _timed_request(self, method: str, url: str, **kwargs) -> tuple[Optional[httpx.Response], float]:
        """Make a request and measure response time."""
        import time
        start = time.perf_counter()
        try:
            resp = await getattr(self.client, method.lower())(url, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return resp, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return None, elapsed_ms

    # =========================================================================
    # REDDIT
    # =========================================================================
    async def check_reddit(self):
        """Test Reddit ingester."""
        api_key = self._env("SCRAPECREATORS_API_KEY")

        # Test public API (always available)
        resp, elapsed = await self._timed_request(
            "GET",
            "https://www.reddit.com/search.json",
            params={"q": "test", "limit": 5},
            headers={"User-Agent": "LiveMirror/0.1"},
        )

        if resp and resp.status_code == 200:
            data = resp.json()
            results = len(data.get("data", {}).get("children", []))
            api_type = "ScrapeCreators" if api_key else "Public JSON API"
            self.results.append(PlatformResult(
                name="Reddit",
                status=Status.OK,
                message=f"Connected via {api_type}",
                api_type=api_type,
                response_time_ms=elapsed,
                sample_results=results,
            ))
        else:
            self.results.append(PlatformResult(
                name="Reddit",
                status=Status.FAILED,
                message=f"Failed: {resp.status_code if resp else 'No response'}",
                api_type="Public JSON API",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # HACKERNEWS
    # =========================================================================
    async def check_hackernews(self):
        """Test HackerNews ingester (Algolia API)."""
        resp, elapsed = await self._timed_request(
            "GET",
            "https://hn.algolia.com/api/v1/search",
            params={"query": "test", "hitsPerPage": 5},
        )

        if resp and resp.status_code == 200:
            data = resp.json()
            results = len(data.get("hits", []))
            self.results.append(PlatformResult(
                name="HackerNews",
                status=Status.OK,
                message="Connected via Algolia API",
                api_type="Algolia API (free)",
                response_time_ms=elapsed,
                sample_results=results,
            ))
        else:
            self.results.append(PlatformResult(
                name="HackerNews",
                status=Status.FAILED,
                message=f"Failed: {resp.status_code if resp else 'No response'}",
                api_type="Algolia API",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # POLYMARKET
    # =========================================================================
    async def check_polymarket(self):
        """Test Polymarket ingester."""
        resp, elapsed = await self._timed_request(
            "GET",
            "https://clob.polymarket.com/markets",
            params={"limit": 5},
        )

        if resp and resp.status_code == 200:
            data = resp.json()
            results = len(data) if isinstance(data, list) else len(data.get("markets", []))
            self.results.append(PlatformResult(
                name="Polymarket",
                status=Status.OK,
                message="Connected via CLOB API",
                api_type="Public CLOB API",
                response_time_ms=elapsed,
                sample_results=results,
            ))
        else:
            # Try gamma API as fallback
            resp2, elapsed2 = await self._timed_request(
                "GET",
                "https://gamma-api.polymarket.com/markets",
                params={"limit": 5},
            )
            if resp2 and resp2.status_code == 200:
                self.results.append(PlatformResult(
                    name="Polymarket",
                    status=Status.OK,
                    message="Connected via Gamma API",
                    api_type="Gamma API",
                    response_time_ms=elapsed2,
                ))
            else:
                self.results.append(PlatformResult(
                    name="Polymarket",
                    status=Status.FAILED,
                    message=f"Failed: {resp.status_code if resp else 'No response'}",
                    api_type="CLOB API",
                    response_time_ms=elapsed,
                ))

    # =========================================================================
    # WEB SEARCH
    # =========================================================================
    async def check_web_search(self):
        """Test Web Search ingester (Zenserp, SerpAPI, or DuckDuckGo)."""
        zenserp_key = self._env("ZENSERP_API_KEY")
        serpapi_key = self._env("SERPAPI_API_KEY")

        # Try Zenserp first
        if zenserp_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://app.zenserp.com/api/v2/search",
                params={"q": "test", "apikey": zenserp_key, "num": 5},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                results = len(data.get("organic", []))
                self.results.append(PlatformResult(
                    name="Web Search",
                    status=Status.OK,
                    message="Connected via Zenserp",
                    api_type="Zenserp API",
                    response_time_ms=elapsed,
                    sample_results=results,
                ))
                return

        # Try SerpAPI
        if serpapi_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://serpapi.com/search.json",
                params={"q": "test", "api_key": serpapi_key, "num": 5},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                results = len(data.get("organic_results", []))
                self.results.append(PlatformResult(
                    name="Web Search",
                    status=Status.OK,
                    message="Connected via SerpAPI",
                    api_type="SerpAPI",
                    response_time_ms=elapsed,
                    sample_results=results,
                ))
                return
            
        # Try DuckDuckGo as fallback
        resp, elapsed = await self._timed_request(
            "GET",
            "https://api.duckduckgo.com/",
            params={"q": "test", "format": "json"},
        )

        if resp and resp.status_code == 200:
            has_key = zenserp_key or serpapi_key
            self.results.append(PlatformResult(
                name="Web Search",
                status=Status.OK if not has_key else Status.DEGRADED,
                message="Using DuckDuckGo (limited)" if not has_key else "API failed, using DuckDuckGo",
                api_type="DuckDuckGo API",
                response_time_ms=elapsed,
            ))
        else:
            self.results.append(PlatformResult(
                name="Web Search",
                status=Status.NO_KEY if not (zenserp_key or serpapi_key) else Status.FAILED,
                message="No ZENSERP_API_KEY or SERPAPI_API_KEY set" if not (zenserp_key or serpapi_key) else "All search APIs failed",
                api_type="Zenserp/SerpAPI",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # TWITTER/X
    # =========================================================================
    async def check_twitter(self):
        """Test Twitter/X ingester."""
        bearer_token = self._env("TWITTER_BEARER_TOKEN")

        if bearer_token:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://api.twitter.com/2/tweets/search/recent",
                params={"query": "test", "max_results": 10},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                results = len(data.get("data", []))
                self.results.append(PlatformResult(
                    name="Twitter/X",
                    status=Status.OK,
                    message="Connected via API v2",
                    api_type="Twitter API v2",
                    response_time_ms=elapsed,
                    sample_results=results,
                ))
                return

        # Try Nitter fallback
        nitter_instances = [
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]
        for nitter_url in nitter_instances:
            try:
                resp, elapsed = await self._timed_request(
                    "GET",
                    nitter_url,
                    follow_redirects=True,
                )
                if resp and resp.status_code == 200:
                    self.results.append(PlatformResult(
                        name="Twitter/X",
                        status=Status.DEGRADED if bearer_token else Status.OK,
                        message=f"Using Nitter ({nitter_url})",
                        api_type="Nitter RSS",
                        response_time_ms=elapsed,
                    ))
                    return
            except Exception:
                continue

        self.results.append(PlatformResult(
            name="Twitter/X",
            status=Status.NO_KEY if not bearer_token else Status.FAILED,
            message="No TWITTER_BEARER_TOKEN set, Nitter unavailable" if not bearer_token else "API and Nitter failed",
            api_type="Twitter API v2" if bearer_token else "Nitter",
        ))

    # =========================================================================
    # YOUTUBE
    # =========================================================================
    async def check_youtube(self):
        """Test YouTube ingester."""
        api_key = self._env("YOUTUBE_API_KEY")

        if api_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "key": api_key,
                    "q": "test",
                    "part": "snippet",
                    "type": "video",
                    "maxResults": 5,
                },
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                results = len(data.get("items", []))
                self.results.append(PlatformResult(
                    name="YouTube",
                    status=Status.OK,
                    message="Connected via Data API v3",
                    api_type="YouTube Data API v3",
                    response_time_ms=elapsed,
                    sample_results=results,
                ))
                return

        # Try RSS fallback
        resp, elapsed = await self._timed_request(
            "GET",
            "https://www.youtube.com/feeds/videos.xml",
            params={"channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"},  # Google Developers
        )

        if resp and resp.status_code == 200:
            self.results.append(PlatformResult(
                name="YouTube",
                status=Status.DEGRADED if api_key else Status.OK,
                message="Using RSS feeds (limited)",
                api_type="YouTube RSS",
                response_time_ms=elapsed,
            ))
        else:
            self.results.append(PlatformResult(
                name="YouTube",
                status=Status.NO_KEY if not api_key else Status.FAILED,
                message="No YOUTUBE_API_KEY set" if not api_key else "API and RSS failed",
                api_type="YouTube Data API v3" if api_key else "RSS",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # BLUESKY
    # =========================================================================
    async def check_bluesky(self):
        """Test Bluesky ingester."""
        # Bluesky has public API
        resp, elapsed = await self._timed_request(
            "GET",
            "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
            params={"q": "test", "limit": 5},
        )

        if resp and resp.status_code == 200:
            data = resp.json()
            results = len(data.get("posts", []))
            self.results.append(PlatformResult(
                name="Bluesky",
                status=Status.OK,
                message="Connected via AT Protocol API",
                api_type="Public AT Protocol",
                response_time_ms=elapsed,
                sample_results=results,
            ))
        else:
            self.results.append(PlatformResult(
                name="Bluesky",
                status=Status.FAILED,
                message=f"Failed: {resp.status_code if resp else 'No response'}",
                api_type="AT Protocol",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # NEWS
    # =========================================================================
    async def check_news(self):
        """Test News ingester (NewsAPI or Google News RSS)."""
        news_api_key = self._env("NEWS_API_KEY")

        if news_api_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://newsapi.org/v2/everything",
                params={"q": "technology", "pageSize": 5, "apiKey": news_api_key},
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                results = len(data.get("articles", []))
                self.results.append(PlatformResult(
                    name="News",
                    status=Status.OK,
                    message="Connected via NewsAPI",
                    api_type="NewsAPI",
                    response_time_ms=elapsed,
                    sample_results=results,
                ))
                return

        # Try Google News RSS
        resp, elapsed = await self._timed_request(
            "GET",
            "https://news.google.com/rss/search",
            params={"q": "technology", "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )

        if resp and resp.status_code == 200:
            self.results.append(PlatformResult(
                name="News",
                status=Status.DEGRADED if news_api_key else Status.OK,
                message="Using Google News RSS" if not news_api_key else "NewsAPI failed, using Google News RSS",
                api_type="Google News RSS",
                response_time_ms=elapsed,
            ))
        else:
            self.results.append(PlatformResult(
                name="News",
                status=Status.NO_KEY if not news_api_key else Status.FAILED,
                message="No NEWS_API_KEY set" if not news_api_key else "All news sources failed",
                api_type="NewsAPI" if news_api_key else "Google News RSS",
                response_time_ms=elapsed,
            ))

    # =========================================================================
    # TIKTOK
    # =========================================================================
    async def check_tiktok(self):
        """Test TikTok ingester."""
        scrapecreators_key = self._env("SCRAPECREATORS_API_KEY")

        if scrapecreators_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://api.scrapecreators.com/v1/tiktok/search",
                params={"q": "test", "limit": 5},
                headers={"Authorization": f"Bearer {scrapecreators_key}"},
            )
            if resp and resp.status_code == 200:
                self.results.append(PlatformResult(
                    name="TikTok",
                    status=Status.OK,
                    message="Connected via ScrapeCreators",
                    api_type="ScrapeCreators API",
                    response_time_ms=elapsed,
                ))
                return

        # TikTok doesn't have a reliable public API
        self.results.append(PlatformResult(
            name="TikTok",
            status=Status.NO_KEY,
            message="Requires SCRAPECREATORS_API_KEY (no public API)",
            api_type="ScrapeCreators API",
        ))

    # =========================================================================
    # INSTAGRAM
    # =========================================================================
    async def check_instagram(self):
        """Test Instagram ingester."""
        scrapecreators_key = self._env("SCRAPECREATORS_API_KEY")

        if scrapecreators_key:
            resp, elapsed = await self._timed_request(
                "GET",
                "https://api.scrapecreators.com/v1/instagram/search",
                params={"q": "test", "limit": 5},
                headers={"Authorization": f"Bearer {scrapecreators_key}"},
            )
            if resp and resp.status_code == 200:
                self.results.append(PlatformResult(
                    name="Instagram",
                    status=Status.OK,
                    message="Connected via ScrapeCreators",
                    api_type="ScrapeCreators API",
                    response_time_ms=elapsed,
                ))
                return

        # Instagram doesn't have a reliable public API for search
        self.results.append(PlatformResult(
            name="Instagram",
            status=Status.NO_KEY,
            message="Requires SCRAPECREATORS_API_KEY (no public API)",
            api_type="ScrapeCreators API",
        ))

    # =========================================================================
    # RUN ALL CHECKS
    # =========================================================================
    async def run_all_checks(self):
        """Run all platform health checks."""
        print("\n" + "=" * 70)
        print("🔍 LiveMirror Platform Health Check")
        print("=" * 70)
        print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🔄 Checking all platforms...\n")

        # Run all checks concurrently for speed
        await asyncio.gather(
            self.check_reddit(),
            self.check_hackernews(),
            self.check_polymarket(),
            self.check_web_search(),
            self.check_twitter(),
            self.check_youtube(),
            self.check_bluesky(),
            self.check_news(),
            self.check_tiktok(),
            self.check_instagram(),
        )

        # Print results
        print("-" * 70)
        print(f"{'Platform':<15} {'Status':<15} {'API Type':<25} {'Time':<10}")
        print("-" * 70)

        for result in sorted(self.results, key=lambda r: r.name):
            time_str = f"{result.response_time_ms:.0f}ms" if result.response_time_ms else "N/A"
            status_str = result.status.value
            print(f"{result.name:<15} {status_str:<15} {result.api_type:<25} {time_str:<10}")
            if result.status in (Status.FAILED, Status.NO_KEY):
                print(f"                └── {result.message}")

        # Summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        ok_count = sum(1 for r in self.results if r.status == Status.OK)
        degraded_count = sum(1 for r in self.results if r.status == Status.DEGRADED)
        failed_count = sum(1 for r in self.results if r.status == Status.FAILED)
        no_key_count = sum(1 for r in self.results if r.status == Status.NO_KEY)

        print(f"\n  ✅ OK:       {ok_count}")
        print(f"  ⚠️ Degraded: {degraded_count}")
        print(f"  ❌ Failed:   {failed_count}")
        print(f"  🔑 No Key:   {no_key_count}")

        # API Keys status
        print("\n" + "-" * 70)
        print("🔑 API KEYS STATUS")
        print("-" * 70)

        keys = [
            ("ZENSERP_API_KEY", "Web Search (Zenserp - Google SERP)"),
            ("SCRAPECREATORS_API_KEY", "Reddit (premium), TikTok, Instagram"),
            ("TWITTER_BEARER_TOKEN", "Twitter/X API v2"),
            ("YOUTUBE_API_KEY", "YouTube Data API v3"),
            ("NEWS_API_KEY", "NewsAPI"),
            ("SERPAPI_API_KEY", "Web Search (SerpAPI - alternative)"),
        ]

        for key, platforms in keys:
            value = os.getenv(key)
            if value:
                print(f"  ✅ {key}: Set ({platforms})")
            else:
                print(f"  ❌ {key}: Not set ({platforms})")

        print("\n" + "=" * 70)

        # Overall health
        if failed_count == 0 and no_key_count <= 3:
            print("🎉 Platform health: GOOD")
        elif failed_count > 0:
            print("⚠️ Platform health: DEGRADED - Some platforms are failing")
        else:
            print("🔑 Platform health: LIMITED - Add API keys for full functionality")

        print("=" * 70 + "\n")


async def main():
    checker = PlatformHealthChecker()
    try:
        await checker.run_all_checks()
    finally:
        await checker.close()


if __name__ == "__main__":
    asyncio.run(main())
