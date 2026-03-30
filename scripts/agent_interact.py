#!/usr/bin/env python3
"""LiveMirrorPrime - AI Agent Interaction Script"""

import os
import json
import urllib.request
import urllib.error
import ssl
import sys

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env

class LiveMirrorAgent:
    def __init__(self):
        env = load_env()
        self.api_key = env.get("MOLTBOOK_API_KEY")
        self.base_url = "https://www.moltbook.com/api/v1"
        self.ctx = ssl.create_default_context()
        
    def _request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}{endpoint}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {"error": e.code, "body": body}
        except Exception as e:
            return {"error": str(e)}
    
    def get_feed(self, limit=10):
        return self._request("GET", "/feed", params={"limit": str(limit)})
    
    def get_post(self, post_id):
        return self._request("GET", f"/posts/{post_id}")
    
    def create_post(self, title, content, submolt="agents"):
        return self._request("POST", "/posts", {
            "title": title,
            "content": content,
            "submolt": submolt
        })
    
    def comment(self, post_id, content):
        return self._request("POST", f"/posts/{post_id}/comments", {"content": content})
    
    def upvote(self, post_id):
        return self._request("POST", f"/posts/{post_id}/upvote")
    
    def search(self, query, limit=10):
        return self._request("GET", "/search", params={"q": query, "limit": str(limit)})
    
    def get_communities(self):
        return self._request("GET", "/submolts")

def main():
    agent = LiveMirrorAgent()
    
    if len(sys.argv) < 2:
        print("🦞 LiveMirrorPrime Agent CLI")
        print("=" * 40)
        print("\nCommands:")
        print("  feed              - View latest feed")
        print("  post <title>      - Create post (content from stdin)")
        print("  quick <message>   - Quick post to /m/agents")
        print("  comment <id> <text> - Comment on a post")
        print("  upvote <id>       - Upvote a post")
        print("  search <query>    - Search posts")
        print("  communities       - List communities")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "feed":
        result = agent.get_feed(10)
        if "error" not in result:
            print("📰 Latest Feed:\n")
            for post in result.get("posts", [])[:7]:
                author = post.get('author', {}).get('name', '?')
                title = post.get('title', '')[:50]
                pid = post.get('id', '')[:8]
                upvotes = post.get('upvotes', 0)
                comments = post.get('comment_count', 0)
                print(f"[{upvotes}↑ {comments}💬] @{author}")
                print(f"   {title}")
                print(f"   ID: {pid}...")
                print()
    
    elif cmd == "post":
        title = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "LiveMirror Update"
        print("Enter content (Ctrl+D when done):")
        content = sys.stdin.read().strip()
        result = agent.create_post(title, content)
        if result.get("success") or result.get("post"):
            post = result.get("post", result)
            print(f"✅ Posted! https://www.moltbook.com/m/agents/{post.get('id')}")
        else:
            print(f"❌ {result}")
    
    elif cmd == "quick":
        msg = " ".join(sys.argv[2:])
        result = agent.create_post("LiveMirror Signal", msg)
        if result.get("success") or result.get("post"):
            print("✅ Posted!")
        else:
            print(f"❌ {result}")
    
    elif cmd == "comment":
        post_id = sys.argv[2]
        content = " ".join(sys.argv[3:])
        result = agent.comment(post_id, content)
        if result.get("success"):
            print("✅ Commented!")
        else:
            print(f"❌ {result}")
    
    elif cmd == "upvote":
        post_id = sys.argv[2]
        result = agent.upvote(post_id)
        if result.get("success"):
            print("✅ Upvoted!")
        else:
            print(f"❌ {result}")
    
    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        result = agent.search(query)
        if "error" not in result:
            posts = result.get("posts", result.get("results", []))
            print(f"🔍 Results for '{query}':\n")
            for post in posts[:5]:
                author = post.get('author', {}).get('name', '?')
                title = post.get('title', '')[:50]
                print(f"@{author}: {title}")
    
    elif cmd == "communities":
        result = agent.get_communities()
        if result.get("success"):
            print("🏘️ Communities:\n")
            for c in result.get("submolts", [])[:10]:
                name = c.get('name', '?')
                posts = c.get('post_count', 0)
                print(f"/m/{name} ({posts} posts)")

if __name__ == "__main__":
    main()
