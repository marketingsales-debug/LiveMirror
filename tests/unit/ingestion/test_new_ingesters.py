"""
Tests for new platform ingesters (Twitter, YouTube, Bluesky, News).
Owner: Claude

Tests ingester interface compliance and data parsing.
Does NOT hit real APIs — uses mocked responses.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.ingestion.platforms.twitter import TwitterIngester
from src.ingestion.platforms.youtube import YouTubeIngester
from src.ingestion.platforms.bluesky import BlueskyIngester
from src.ingestion.platforms.news import NewsIngester
from src.shared.types import Platform


class TestTwitterIngester:
    def test_platform_is_twitter(self):
        ingester = TwitterIngester()
        assert ingester.platform == Platform.TWITTER

    def test_nitter_rss_parsing(self):
        ingester = TwitterIngester()
        xml = """<?xml version="1.0"?>
        <rss><channel>
        <item>
            <title>Test tweet about AI</title>
            <link>https://nitter.net/user/status/123</link>
            <description>This is a test tweet about AI regulation</description>
            <pubDate>Thu, 27 Mar 2026 10:00:00 GMT</pubDate>
            <dc:creator>testuser</dc:creator>
        </item>
        </channel></rss>"""

        since = datetime(2026, 1, 1)
        signals = ingester._parse_nitter_rss(xml, since, 10)
        assert len(signals) == 1
        assert signals[0].platform == Platform.TWITTER
        assert "AI regulation" in signals[0].content
        assert signals[0].author == "testuser"

    def test_nitter_rss_filters_old(self):
        ingester = TwitterIngester()
        xml = """<?xml version="1.0"?>
        <rss><channel>
        <item>
            <title>Old tweet</title>
            <description>Old content</description>
            <pubDate>Thu, 01 Jan 2025 10:00:00 GMT</pubDate>
        </item>
        </channel></rss>"""

        since = datetime(2026, 1, 1)
        signals = ingester._parse_nitter_rss(xml, since, 10)
        assert len(signals) == 0


class TestYouTubeIngester:
    def test_platform_is_youtube(self):
        ingester = YouTubeIngester()
        assert ingester.platform == Platform.YOUTUBE


class TestBlueskyIngester:
    def test_platform_is_bluesky(self):
        ingester = BlueskyIngester()
        assert ingester.platform == Platform.BLUESKY


class TestNewsIngester:
    def test_platform_is_news(self):
        ingester = NewsIngester()
        assert ingester.platform == Platform.NEWS
