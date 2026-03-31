import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.ingestion.platforms.bluesky import BlueskyIngester

async def test_bluesky():
    print("🔍 Testing Bluesky Ingester...")
    ingester = BlueskyIngester()
    
    # Test health check
    healthy = await ingester.health_check()
    print(f"Health Check: {'✅ PASSED' if healthy else '❌ FAILED'}")
    
    if not healthy:
        # Debug why it failed
        import httpx
        try:
            async with httpx.AsyncClient(headers={"User-Agent": "LiveMirror/2.0"}) as client:
                resp = await client.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts", params={"q": "test", "limit": 1})
                print(f"Debug Status: {resp.status_code}")
                print(f"Debug Response: {resp.text[:200]}")
        except Exception as e:
            print(f"Debug Error: {e}")

    # Test search
    signals = await ingester.search("AI Regulation", max_results=5)
    print(f"Search Results: {len(signals)} signals found")
    for s in signals:
        print(f"- [{s.author}] {s.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_bluesky())
