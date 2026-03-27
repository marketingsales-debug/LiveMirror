"""
Agent Behavior Engine — decides what each agent does each round.
Owner: Claude

Each agent has a behavioral fingerprint (from real data) that determines:
- When they're active (time-of-day probability)
- What actions they take (post, comment, react, share)
- How they're influenced by other agents (trust network + persuadability)
- How their beliefs evolve over time
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict

from ...shared.types import AgentPersona, AgentRole, Stance


class ActionType(str, Enum):
    CREATE_POST = "CREATE_POST"
    COMMENT = "COMMENT"
    LIKE = "LIKE"
    SHARE = "SHARE"
    IGNORE = "IGNORE"


# Role-based action probability weights
# {role: {action: weight}}
ROLE_ACTION_WEIGHTS: Dict[AgentRole, Dict[ActionType, float]] = {
    AgentRole.INDIVIDUAL: {
        ActionType.LIKE: 0.50,
        ActionType.COMMENT: 0.25,
        ActionType.SHARE: 0.15,
        ActionType.CREATE_POST: 0.05,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.INFLUENCER: {
        ActionType.CREATE_POST: 0.35,
        ActionType.COMMENT: 0.30,
        ActionType.SHARE: 0.20,
        ActionType.LIKE: 0.10,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.MEDIA: {
        ActionType.CREATE_POST: 0.55,
        ActionType.SHARE: 0.25,
        ActionType.COMMENT: 0.10,
        ActionType.LIKE: 0.05,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.ORGANIZATION: {
        ActionType.CREATE_POST: 0.40,
        ActionType.SHARE: 0.30,
        ActionType.COMMENT: 0.20,
        ActionType.LIKE: 0.05,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.GOVERNMENT: {
        ActionType.CREATE_POST: 0.50,
        ActionType.COMMENT: 0.20,
        ActionType.SHARE: 0.20,
        ActionType.LIKE: 0.05,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.EXPERT: {
        ActionType.COMMENT: 0.40,
        ActionType.CREATE_POST: 0.30,
        ActionType.SHARE: 0.15,
        ActionType.LIKE: 0.10,
        ActionType.IGNORE: 0.05,
    },
    AgentRole.BOT: {
        ActionType.LIKE: 0.40,
        ActionType.SHARE: 0.35,
        ActionType.COMMENT: 0.15,
        ActionType.CREATE_POST: 0.08,
        ActionType.IGNORE: 0.02,
    },
}


@dataclass
class AgentDecision:
    """A single agent's decision for one round."""
    agent_id: int
    action: ActionType
    sentiment: float          # -1 to 1 — what this action expresses
    influence_delta: float    # how much influence this action spreads
    target_agent_id: Optional[int] = None
    content_summary: str = ""


class AgentBehaviorEngine:
    """
    Decides what agents do each round and propagates influence between them.

    Design principles:
    - Deterministic when seeded (for reproducible tests)
    - Stance biases sentiment but peer influence can shift it
    - Trust network controls who influences whom
    - Echo chamber score controls how resistant agents are to outside views
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def should_activate(self, agent: AgentPersona, round_num: int) -> bool:
        """
        Decide if an agent acts this round.
        Based on activity_level and active_hours from their fingerprint.
        round_num maps to hour-of-day (0-23) cyclically.
        """
        hour = round_num % 24
        active_hours = agent.fingerprint.active_hours or list(range(9, 23))

        if hour not in active_hours:
            # Small chance of off-hours activity
            return self._rng.random() < 0.05

        return self._rng.random() < agent.activity_level

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def decide_action(
        self,
        agent: AgentPersona,
        topic_sentiment: float,
        recent_actions: List[AgentDecision],
    ) -> AgentDecision:
        """
        Pick an action for this agent, weighted by role and influenced
        by recent peer actions visible in this round.
        """
        weights = ROLE_ACTION_WEIGHTS.get(agent.role, ROLE_ACTION_WEIGHTS[AgentRole.INDIVIDUAL])
        actions = list(weights.keys())
        probs = list(weights.values())

        action = self._rng.choices(actions, weights=probs, k=1)[0]

        # Sentiment = agent's stance bias + noise + peer pull
        peer_pull = self._compute_peer_pull(agent, recent_actions)
        base_sentiment = agent.sentiment_bias
        noise = self._rng.gauss(0, 0.1)
        sentiment = max(-1.0, min(1.0, base_sentiment + peer_pull + noise))

        # Influence delta: how impactful is this action
        influence = self._compute_influence(agent, action)

        # Pick a target from recent actors if commenting/sharing
        target_id = None
        if action in (ActionType.COMMENT, ActionType.LIKE, ActionType.SHARE):
            candidates = [d for d in recent_actions if d.agent_id != agent.agent_id]
            if candidates:
                target = self._rng.choice(candidates)
                target_id = target.agent_id

        return AgentDecision(
            agent_id=agent.agent_id,
            action=action,
            sentiment=sentiment,
            influence_delta=influence,
            target_agent_id=target_id,
        )

    # ------------------------------------------------------------------
    # Influence propagation
    # ------------------------------------------------------------------

    def apply_influence(
        self,
        agent: AgentPersona,
        round_decisions: List[AgentDecision],
    ) -> float:
        """
        Apply other agents' actions to this agent's belief state.
        Returns the magnitude of belief shift.

        Echo chamber score controls how much outside views penetrate:
        - 1.0 = total echo chamber, only trusted agents matter
        - 0.0 = open to all influence equally
        """
        if not round_decisions:
            return 0.0

        echo = agent.fingerprint.echo_chamber_score
        persuadability = agent.fingerprint.persuadability
        trust_net = agent.trust_network

        total_influence = 0.0
        total_weight = 0.0

        for decision in round_decisions:
            if decision.agent_id == agent.agent_id:
                continue
            if decision.action == ActionType.IGNORE:
                continue

            trust = trust_net.get(decision.agent_id, 0.5)

            # Echo chamber: low-trust agents have reduced influence
            echo_filter = trust if echo > 0.5 else 1.0
            weight = decision.influence_delta * echo_filter * (1.0 - echo * 0.5)

            total_influence += decision.sentiment * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        avg_influence = total_influence / total_weight
        shift = avg_influence * persuadability

        # Update agent's bias with exponential smoothing
        old_bias = agent.sentiment_bias
        agent.sentiment_bias = max(-1.0, min(1.0, old_bias * 0.95 + shift * 0.05))

        # Record belief history
        if abs(shift) > 0.001:
            agent.belief_history.append({
                "shift": shift,
                "incoming_sentiment": avg_influence,
                "new_bias": agent.sentiment_bias,
            })

        return abs(shift)

    # ------------------------------------------------------------------
    # Trust updates
    # ------------------------------------------------------------------

    def update_trust(
        self,
        agent: AgentPersona,
        other_id: int,
        action: ActionType,
        alignment: float,
    ) -> None:
        """
        Update trust toward another agent based on interaction type and alignment.

        Positive actions (LIKE, SHARE) toward aligned agents build trust.
        COMMENT can build or erode trust depending on alignment.
        """
        delta = 0.0

        if action == ActionType.LIKE:
            delta = 0.02 * alignment
        elif action == ActionType.SHARE:
            delta = 0.03 * alignment
        elif action == ActionType.COMMENT:
            delta = 0.01 * (alignment - 0.5)  # can be negative
        elif action == ActionType.CREATE_POST:
            delta = 0.005 * alignment

        agent.update_trust(other_id, delta)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_peer_pull(
        self,
        agent: AgentPersona,
        recent_actions: List[AgentDecision],
    ) -> float:
        """
        How much do recent peer actions pull this agent's sentiment?
        Trust-weighted, scaled by persuadability.
        """
        if not recent_actions:
            return 0.0

        trust_net = agent.trust_network
        persuadability = agent.fingerprint.persuadability

        weighted_sum = 0.0
        weight_total = 0.0

        for decision in recent_actions:
            if decision.agent_id == agent.agent_id:
                continue
            trust = trust_net.get(decision.agent_id, 0.3)
            weighted_sum += decision.sentiment * trust
            weight_total += trust

        if weight_total == 0:
            return 0.0

        avg = weighted_sum / weight_total
        return avg * persuadability * 0.2  # cap peer pull at 20% of persuadability

    def _compute_influence(self, agent: AgentPersona, action: ActionType) -> float:
        """
        How much influence does this action have?
        Based on agent's influence_weight and action type.
        """
        action_multipliers = {
            ActionType.CREATE_POST: 1.0,
            ActionType.SHARE: 0.8,
            ActionType.COMMENT: 0.6,
            ActionType.LIKE: 0.3,
            ActionType.IGNORE: 0.0,
        }
        base = agent.influence_weight * action_multipliers.get(action, 0.5)
        noise = self._rng.gauss(0, 0.05)
        return max(0.0, base + noise)
