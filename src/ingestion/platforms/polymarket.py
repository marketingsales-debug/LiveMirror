"""
Polymarket ingester — pulls prediction market data.
Owner: Claude

Uses the free Polymarket public API. No key needed.
Prediction markets are a powerful calibration signal.
"""

from typing import List, Optional
from datetime import datetime

import httpx

from ...shared.types import RawSignal, Platform, SignalType
from ..base import BaseIngester


class PolymarketIngester(BaseIngester):
    """Ingest prediction market data from Polymarket."""

    platform = Platform.POLYMARKET
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[RawSignal]:
        signals: List[RawSignal] = []
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/markets",
                params={
                    "search": query,
                    "limit": min(max_results, 50),
                    "active": "true",
                },
            )
            resp.raise_for_status()
            markets = resp.json()

            if not isinstance(markets, list):
                markets = markets.get("results", [])

            for market in markets:
                # Extract outcome probabilities
                outcomes = market.get("outcomes", [])
                outcome_prices = market.get("outcomePrices", [])
                probabilities = {}
                for i, outcome in enumerate(outcomes):
                    if i < len(outcome_prices):
                        try:
                            probabilities[outcome] = float(outcome_prices[i])
                        except (ValueError, TypeError):
                            pass

                volume = market.get("volume", 0)
                try:
                    volume = float(volume)
                except (ValueError, TypeError):
                    volume = 0

                signals.append(RawSignal(
                    platform=Platform.POLYMARKET,
                    signal_type=SignalType.PREDICTION_MARKET,
                    content=market.get("question", market.get("title", "")),
                    url=f"https://polymarket.com/event/{market.get('slug', '')}",
                    timestamp=datetime.now(),
                    engagement={
                        "volume": int(volume),
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                    },
                    metadata={
                        "market_id": market.get("id"),
                        "probabilities": probabilities,
                        "end_date": market.get("endDate"),
                        "category": market.get("category"),
                        "liquidity": market.get("liquidity"),
                    },
                    raw_data=market,
                ))

        except Exception as e:
            print(f"[Polymarket] Search failed: {e}")

        return signals[:max_results]

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/markets",
                params={"limit": 1, "active": "true"},
            )
            return resp.status_code == 200
        except Exception:
            return False
