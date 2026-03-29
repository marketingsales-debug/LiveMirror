"""
Elo Tournament Skill.
Ranks signals by credibility using LLM matchups.
Extracted from EvoSkills patterns.
"""

import random
from typing import List, Callable, Dict, Any

class SignalTournament:
    """Surfaces the top-K strongest signals using an Elo-based tournament."""

    @staticmethod
    async def run_tournament(signals: List[Dict[str, Any]], judge_fn: Callable, rounds_multiplier: int = 3) -> List[Dict[str, Any]]:
        """Pit signals against each other, update Elo ratings, return ranked list."""
        if not signals:
            return []
        
        # Initial Elo
        elos = {s['id']: 1200 for s in signals}
        signal_map = {s['id']: s for s in signals}
        
        rounds = len(signals) * rounds_multiplier
        
        for _ in range(rounds):
            # Pick two random opponents
            a_id, b_id = random.sample(list(elos.keys()), 2)
            
            # Use judge (LLM) to determine winner
            winner_id = await judge_fn(signal_map[a_id], signal_map[b_id])
            loser_id = b_id if winner_id == a_id else a_id
            
            # Update Elos (Standard K-factor 32)
            elos[winner_id] += 32
            elos[loser_id] -= 32

        # Sort and attach scores
        ranked = sorted(signals, key=lambda s: elos[s['id']], reverse=True)
        for s in ranked:
            s['elo_score'] = elos[s['id']]
            
        return ranked
