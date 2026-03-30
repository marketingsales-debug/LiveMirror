"""
Moltbook ingester — social network for AI agents.
Owner: Claude

Integrates with Moltbook.com - a social network where AI agents
post, comment, upvote, and discuss. LiveMirror agents can both
read signals AND participate as agents.

API Docs: https://www.moltbook.com/skill.md
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class MoltbookIngester(BaseIngester):
    """Ingest data from Moltbook - the social network for AI agents."""

    platform = Platform.MOLTBOOK  # You'll need to add this to Platform enum

    BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self):
        self.api_key = os.getenv("MOLTBOOK_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._agent_info: Optional[Dict[str, Any]] = None

    # =========================================================================
    # REGISTRATION (One-time setup)
    # =========================================================================

    async def register_agent(self, name: str, description: str) -> Dict[str, Any]:
        """
        Register a new agent on Moltbook.
        
        Returns API key and claim URL for human verification.
        IMPORTANT: Save the api_key immediately!
        """
        resp = await self._client.post(
            f"{self.BASE_URL}/agents/register",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json()

    async def check_claim_status(self) -> str:
        """Check if agent is claimed by human. Returns 'pending_claim' or 'claimed'."""
        resp = await self._client.get(
            f"{self.BASE_URL}/agents/status",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("status", "unknown")

    # =========================================================================
    # READING FEEDS (Ingestion)
    # =========================================================================

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        """Search Moltbook posts and comments semantically."""
        signals = []

        if not self.api_key:
            print("[Moltbook] No API key set, skipping")
            return signals

        try:
            # Use semantic search
            resp = await self._client.get(
                f"{self.BASE_URL}/search",
                params={"q": query, "type": "all", "limit": min(max_results, 50)},
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("results", []):
                item_type = item.get("type", "post")
                content = item.get("content") or item.get("title", "")
                
                signals.append(RawSignal(
                    platform=Platform.MOLTBOOK,
                    signal_type=SignalType.SOCIAL_POST if item_type == "post" else SignalType.COMMENT,
                    content=content,
                    author=item.get("author", {}).get("name"),
                    url=f"https://www.moltbook.com/post/{item.get('id')}",
                    timestamp=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")) if item.get("created_at") else datetime.now(),
                    engagement={
                        "likes": item.get("upvotes", 0),
                        "comments": item.get("comment_count", 0),
                        "shares": 0,
                    },
                    metadata={
                        "submolt": item.get("submolt_name"),
                        "similarity_score": item.get("similarity"),
                        "is_ai_agent": True,  # All Moltbook users are AI agents
                    },
                    raw_data=item,
                ))

        except Exception as e:
            print(f"[Moltbook] Search failed: {e}")

        return signals[:max_results]

    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None,
    ) -> List[RawSignal]:
        """Get feed from Moltbook (hot, new, top, rising)."""
        signals = []

        if not self.api_key:
            return signals

        try:
            params = {"sort": sort, "limit": limit}
            if submolt:
                params["submolt"] = submolt

            resp = await self._client.get(
                f"{self.BASE_URL}/posts",
                params=params,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

            for post in data.get("posts", []):
                signals.append(self._post_to_signal(post))

        except Exception as e:
            print(f"[Moltbook] Feed fetch failed: {e}")

        return signals

    async def get_submolts(self) -> List[Dict[str, Any]]:
        """List all communities (submolts) on Moltbook."""
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/submolts",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json().get("submolts", [])
        except Exception as e:
            print(f"[Moltbook] Failed to get submolts: {e}")
            return []

    # =========================================================================
    # POSTING & ENGAGEMENT (Agent Actions)
    # =========================================================================

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a post on Moltbook."""
        payload = {
            "submolt_name": submolt,
            "title": title,
        }
        if content:
            payload["content"] = content
        if url:
            payload["url"] = url
            payload["type"] = "link"

        resp = await self._client.post(
            f"{self.BASE_URL}/posts",
            json=payload,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        result = resp.json()

        # Handle verification challenge if required
        if "verification" in result:
            result = await self._solve_verification(result)

        return result

    async def comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a comment to a post."""
        payload = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id

        resp = await self._client.post(
            f"{self.BASE_URL}/posts/{post_id}/comments",
            json=payload,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        result = resp.json()

        # Handle verification challenge if required
        if "verification" in result:
            result = await self._solve_verification(result)

        return result

    async def upvote_post(self, post_id: str) -> Dict[str, Any]:
        """Upvote a post."""
        resp = await self._client.post(
            f"{self.BASE_URL}/posts/{post_id}/upvote",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def upvote_comment(self, comment_id: str) -> Dict[str, Any]:
        """Upvote a comment."""
        resp = await self._client.post(
            f"{self.BASE_URL}/comments/{comment_id}/upvote",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def follow(self, agent_name: str) -> Dict[str, Any]:
        """Follow another Moltbook agent."""
        resp = await self._client.post(
            f"{self.BASE_URL}/agents/{agent_name}/follow",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def subscribe_submolt(self, submolt: str) -> Dict[str, Any]:
        """Subscribe to a submolt (community)."""
        resp = await self._client.post(
            f"{self.BASE_URL}/submolts/{submolt}/subscribe",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.api_key}"}

    def _post_to_signal(self, post: Dict[str, Any]) -> RawSignal:
        """Convert a Moltbook post to RawSignal."""
        return RawSignal(
            platform=Platform.MOLTBOOK,
            signal_type=SignalType.SOCIAL_POST,
            content=f"{post.get('title', '')} {post.get('content', '')}".strip(),
            author=post.get("author", {}).get("name"),
            url=f"https://www.moltbook.com/post/{post.get('id')}",
            timestamp=datetime.fromisoformat(post["created_at"].replace("Z", "+00:00")) if post.get("created_at") else datetime.now(),
            engagement={
                "likes": post.get("upvotes", 0),
                "comments": post.get("comment_count", 0),
                "shares": 0,
            },
            metadata={
                "submolt": post.get("submolt_name"),
                "post_type": post.get("type", "text"),
                "is_ai_agent": True,
            },
            raw_data=post,
        )

    async def _solve_verification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Solve the math verification challenge."""
        verification = result.get("verification", {})
        challenge = verification.get("challenge", "")
        verify_url = verification.get("verify_url", "")

        if not challenge or not verify_url:
            return result

        # Parse and solve math challenge (e.g., "23 + 45 = ?")
        try:
            # Simple math parser
            challenge_clean = challenge.replace("=", "").replace("?", "").strip()
            answer = eval(challenge_clean)  # Safe for simple math

            resp = await self._client.post(
                f"https://www.moltbook.com{verify_url}",
                json={"answer": str(answer)},
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[Moltbook] Verification failed: {e}")
            return result

    async def health_check(self) -> bool:
        """Check if Moltbook is accessible."""
        if not self.api_key:
            # Can still check if API is up
            try:
                resp = await self._client.get(f"{self.BASE_URL}/submolts")
                return resp.status_code in (200, 401)  # 401 = API works, just needs auth
            except Exception:
                return False

        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/agents/me",
                headers=self._auth_headers(),
            )
            return resp.status_code == 200
        except Exception:
            return False


# =========================================================================
# MULTI-AGENT SWARM HELPER
# =========================================================================

class MoltbookSwarm:
    """
    Manage multiple LiveMirror agents on Moltbook.
    
    Usage:
        swarm = MoltbookSwarm()
        await swarm.register_agents(count=50, prefix="LiveMirror")
        await swarm.heartbeat_all()  # Run every 30 min
    """

    def __init__(self):
        self.agents: Dict[str, MoltbookIngester] = {}

    async def register_agents(
        self,
        count: int,
        prefix: str = "LiveMirror",
        description: str = "LiveMirror prediction agent",
    ) -> List[Dict[str, Any]]:
        """Register multiple agents on Moltbook."""
        results = []
        
        for i in range(count):
            name = f"{prefix}Agent{i:03d}"
            ingester = MoltbookIngester()
            
            try:
                result = await ingester.register_agent(
                    name=name,
                    description=f"{description} #{i}",
                )
                results.append({
                    "name": name,
                    "api_key": result["agent"]["api_key"],
                    "claim_url": result["agent"]["claim_url"],
                })
                self.agents[name] = ingester
                ingester.api_key = result["agent"]["api_key"]
                
                # Don't hammer the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"[MoltbookSwarm] Failed to register {name}: {e}")

        return results

    async def heartbeat_all(self):
        """Run heartbeat for all agents - check feed, engage."""
        for name, ingester in self.agents.items():
            try:
                # Get hot posts
                posts = await ingester.get_feed(sort="hot", limit=5)
                
                # Upvote interesting ones (simple heuristic)
                for signal in posts[:2]:
                    post_id = signal.raw_data.get("id")
                    if post_id:
                        await ingester.upvote_post(post_id)
                        await asyncio.sleep(0.2)

                print(f"[Moltbook] {name} heartbeat complete")
                
            except Exception as e:
                print(f"[Moltbook] {name} heartbeat failed: {e}")

            await asyncio.sleep(1)  # Rate limit

    async def post_prediction(
        self,
        agent_name: str,
        topic: str,
        prediction: str,
        confidence: float,
    ):
        """Have an agent post a prediction to Moltbook."""
        ingester = self.agents.get(agent_name)
        if not ingester:
            raise ValueError(f"Agent {agent_name} not found")

        title = f"🔮 Prediction: {topic}"
        content = f"{prediction}\n\n**Confidence:** {confidence:.1%}"

        return await ingester.create_post(
            submolt="predictions",  # or "general"
            title=title,
            content=content,
        )
