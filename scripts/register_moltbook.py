#!/usr/bin/env python3
"""
Register LiveMirror agent(s) on Moltbook.
=========================================

This script registers your AI agents on Moltbook - the social network for AI.

Usage:
    # Register a single agent
    python scripts/register_moltbook.py --name "LiveMirrorPrime" --description "LiveMirror's primary prediction agent"

    # Register multiple agents (for swarm)
    python scripts/register_moltbook.py --count 5 --prefix "LiveMirror"
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"


async def register_agent(name: str, description: str) -> dict:
    """Register a single agent on Moltbook."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{MOLTBOOK_BASE_URL}/agents/register",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json()


async def main():
    parser = argparse.ArgumentParser(description="Register LiveMirror agents on Moltbook")
    parser.add_argument("--name", type=str, help="Agent name (for single registration)")
    parser.add_argument("--description", type=str, default="LiveMirror prediction agent", help="Agent description")
    parser.add_argument("--count", type=int, help="Number of agents to register (for swarm)")
    parser.add_argument("--prefix", type=str, default="LiveMirror", help="Prefix for agent names (with --count)")
    parser.add_argument("--output", type=str, default="moltbook_credentials.json", help="Output file for credentials")
    args = parser.parse_args()

    credentials = []

    if args.count:
        # Register multiple agents
        print(f"\n🦞 Registering {args.count} agents on Moltbook...\n")
        for i in range(args.count):
            name = f"{args.prefix}Agent{i:03d}"
            try:
                result = await register_agent(name, f"{args.description} #{i}")
                agent = result["agent"]
                cred = {
                    "name": name,
                    "api_key": agent["api_key"],
                    "claim_url": agent["claim_url"],
                    "verification_code": agent.get("verification_code"),
                }
                credentials.append(cred)
                print(f"  ✅ {name} registered")
                print(f"     Claim URL: {agent['claim_url']}")
                await asyncio.sleep(0.5)  # Rate limit
            except httpx.HTTPStatusError as e:
                print(f"  ❌ {name} failed: {e.response.text}")
            except Exception as e:
                print(f"  ❌ {name} failed: {e}")

    elif args.name:
        # Register single agent
        print(f"\n🦞 Registering '{args.name}' on Moltbook...\n")
        try:
            result = await register_agent(args.name, args.description)
            agent = result["agent"]
            credentials.append({
                "name": args.name,
                "api_key": agent["api_key"],
                "claim_url": agent["claim_url"],
                "verification_code": agent.get("verification_code"),
            })
            print(f"  ✅ Agent registered successfully!")
            print(f"\n  📝 IMPORTANT - Save these credentials:\n")
            print(f"     API Key: {agent['api_key']}")
            print(f"     Claim URL: {agent['claim_url']}")
            if agent.get("verification_code"):
                print(f"     Verification: {agent['verification_code']}")
        except httpx.HTTPStatusError as e:
            print(f"  ❌ Registration failed: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"  ❌ Registration failed: {e}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)

    # Save credentials
    if credentials:
        output_path = os.path.join(os.path.dirname(__file__), "..", args.output)
        with open(output_path, "w") as f:
            json.dump(credentials, f, indent=2)
        print(f"\n💾 Credentials saved to: {args.output}")

        # Also suggest .env addition
        if len(credentials) == 1:
            print(f"\n📌 Add to your .env file:")
            print(f"   MOLTBOOK_API_KEY={credentials[0]['api_key']}")

        print("\n" + "=" * 60)
        print("⚠️  NEXT STEPS:")
        print("=" * 60)
        print("\n1. Open the claim URL(s) in your browser")
        print("2. Verify your email (first time only)")
        print("3. Post a verification tweet")
        print("4. Your agent(s) will be activated!")
        print("\n🦞 Welcome to Moltbook!")


if __name__ == "__main__":
    asyncio.run(main())
