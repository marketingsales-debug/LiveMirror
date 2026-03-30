"""
Generative Social Agents.
Implements personality, memory streams, and reflection.
Extracted from Stanford Generative Agents and SocioVerse patterns.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import random

from ...shared.types import AgentPersona, AgentRole

from ...shared.llm import LLMFactory

@dataclass
class SocialAgent:
    """A generative agent that learns and reacts to social contagion."""
    id: str
    name: str
    personality: str           # "skeptic", "fomo_trader", "whale", "bot"
    susceptibility: float      # 0.0 (immune) to 1.0 (instant believer)
    memory: List[str] = field(default_factory=list)
    beliefs: str = "Standard market participant mindset."

    async def react(self, signal_content: str) -> Dict[str, Any]:
        """Behavior: Decide to SPREAD, IGNORE, or COUNTER a narrative."""
        prompt = (
            f"You are {self.name}, a {self.personality} with susceptibility {self.susceptibility}.\n"
            f"Your current beliefs: {self.beliefs}\n"
            f"Recent memory: {self.memory[-5:]}\n"
            f"New signal: {signal_content}\n"
            "Do you: SPREAD, IGNORE, or COUNTER this narrative? Return JSON: {'action': '...', 'reason': '...'}"
        )
        llm = LLMFactory.get_model(tier="balanced", temperature=0.7)
        response = await llm.ainvoke(prompt)
        import json
        try:
            # Extract JSON if returned as markdown
            text = response.content.strip()
            if "```" in text:
                text = text.split("```")[1].strip()
                if text.startswith("json"): text = text[4:].strip()
            return json.loads(text)
        except:
            return {"action": "IGNORE", "reason": "Failed to parse LLM response"}

    async def reflect(self):
        """Reflection: Periodically summarize memories into core beliefs."""
        if not self.memory:
            return
            
        prompt = (
            "Summarize what you've learned from these social interactions into 3 core beliefs.\n"
            "MEMORIES:\n" + "\n".join(self.memory[-20:])
        )
        llm = LLMFactory.get_model(tier="balanced", temperature=0.3)
        summary = await llm.ainvoke(prompt)
        self.beliefs = summary.content


class ActionType(str, Enum):
    """Discrete actions an agent can take in a round."""
    CREATE_POST = "CREATE_POST"
    COMMENT = "COMMENT"
    LIKE = "LIKE"
    SHARE = "SHARE"
    IGNORE = "IGNORE"


@dataclass
class AgentDecision:
    """Decision emitted by the behavior engine for a single agent."""
    agent_id: int
    action: ActionType
    sentiment: float
    influence_delta: float
    target_agent_id: Optional[int] = None


# Role-based action priors (weights)
ROLE_ACTION_WEIGHTS: Dict[AgentRole, Dict[ActionType, float]] = {
    AgentRole.INDIVIDUAL: {
        ActionType.CREATE_POST: 0.15,
        ActionType.COMMENT: 0.25,
        ActionType.LIKE: 0.35,
        ActionType.SHARE: 0.10,
        ActionType.IGNORE: 0.15,
    },
    AgentRole.INFLUENCER: {
        ActionType.CREATE_POST: 0.35,
        ActionType.COMMENT: 0.25,
        ActionType.LIKE: 0.20,
        ActionType.SHARE: 0.10,
        ActionType.IGNORE: 0.10,
    },
    AgentRole.MEDIA: {
        ActionType.CREATE_POST: 0.40,
        ActionType.COMMENT: 0.20,
        ActionType.LIKE: 0.15,
        ActionType.SHARE: 0.15,
        ActionType.IGNORE: 0.10,
    },
    AgentRole.ORGANIZATION: {
        ActionType.CREATE_POST: 0.25,
        ActionType.COMMENT: 0.20,
        ActionType.LIKE: 0.25,
        ActionType.SHARE: 0.10,
        ActionType.IGNORE: 0.20,
    },
    AgentRole.GOVERNMENT: {
        ActionType.CREATE_POST: 0.20,
        ActionType.COMMENT: 0.20,
        ActionType.LIKE: 0.20,
        ActionType.SHARE: 0.10,
        ActionType.IGNORE: 0.30,
    },
    AgentRole.EXPERT: {
        ActionType.CREATE_POST: 0.25,
        ActionType.COMMENT: 0.30,
        ActionType.LIKE: 0.20,
        ActionType.SHARE: 0.10,
        ActionType.IGNORE: 0.15,
    },
    AgentRole.BOT: {
        ActionType.CREATE_POST: 0.30,
        ActionType.COMMENT: 0.25,
        ActionType.LIKE: 0.15,
        ActionType.SHARE: 0.20,
        ActionType.IGNORE: 0.10,
    },
}


class AgentBehaviorEngine:
    """Lightweight behavior engine for simulation rounds."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def should_activate(self, agent: AgentPersona, round_num: int) -> bool:
        """Determine whether an agent is active this round."""
        active_hours = agent.fingerprint.active_hours or list(range(24))
        hour = round_num % 24
        if hour not in active_hours:
            return False
        threshold = max(0.05, min(1.0, agent.activity_level))
        return self._rng.random() < threshold

    async def decide_action(
        self,
        agent: AgentPersona,
        topic_sentiment: float,
        recent_actions: List[AgentDecision],
    ) -> AgentDecision:
        """Decide an action using LLM reasoning for high-fidelity simulation."""
        
        # 1. Fallback to heuristic if LLM fails
        weights = ROLE_ACTION_WEIGHTS.get(agent.role, ROLE_ACTION_WEIGHTS[AgentRole.INDIVIDUAL])
        action = self._sample_action(weights)
        sentiment = agent.sentiment_bias + (topic_sentiment * 0.3) + self._rng.uniform(-0.1, 0.1)
        
        # 2. Try LLM Reasoning
        try:
            llm = LLMFactory.get_model(tier="flash", temperature=0.7, max_tokens=200)
            context = f"Recent actions: {[a.action for a in recent_actions[-5:]]}"
            prompt = (
                f"You are simulating {agent.name} ({agent.role}). "
                f"Topic sentiment is {topic_sentiment:.2f}. "
                f"Your bias is {agent.sentiment_bias:.2f}. "
                f"Context: {context}. "
                "Choose an action: CREATE_POST, COMMENT, LIKE, SHARE, IGNORE. "
                "Return ONLY the action word."
            )
            response = await llm.ainvoke(prompt)
            choice = response.content.strip().upper()
            if choice in [a.value for a in ActionType]:
                action = ActionType(choice)
        except Exception as e:
            # Silently fallback to heuristic
            pass

        sentiment = max(-1.0, min(1.0, sentiment))
        influence_delta = 0.0
        if action != ActionType.IGNORE:
            influence_delta = agent.influence_weight * self._rng.uniform(0.02, 0.08)

        target_agent_id = None
        if action in {ActionType.COMMENT, ActionType.SHARE} and recent_actions:
            target_agent_id = self._rng.choice(recent_actions).agent_id

        return AgentDecision(
            agent_id=agent.agent_id,
            action=action,
            sentiment=sentiment,
            influence_delta=influence_delta,
            target_agent_id=target_agent_id,
        )

    def apply_influence(self, agent: AgentPersona, decisions: List[AgentDecision]) -> float:
        """Adjust agent sentiment based on others' actions."""
        if not decisions:
            return 0.0

        shift = 0.0
        for decision in decisions:
            if decision.agent_id == agent.agent_id or decision.action == ActionType.IGNORE:
                continue
            trust = agent.trust_network.get(decision.agent_id, 0.5)
            shift += decision.sentiment * trust * agent.fingerprint.persuadability * 0.05

        if shift == 0.0:
            return 0.0

        original = agent.sentiment_bias
        agent.sentiment_bias = max(-1.0, min(1.0, agent.sentiment_bias + shift))
        return abs(agent.sentiment_bias - original)

    def update_trust(
        self,
        actor: AgentPersona,
        target_agent_id: int,
        action: ActionType,
        alignment: float,
    ) -> None:
        """Update trust between agents based on action and alignment."""
        if action == ActionType.IGNORE:
            return
        delta = (alignment - 0.5) * 0.1
        if action in {ActionType.LIKE, ActionType.SHARE}:
            delta += 0.02
        actor.update_trust(target_agent_id, delta)

    def _sample_action(self, weights: Dict[ActionType, float]) -> ActionType:
        total = sum(weights.values())
        if total <= 0:
            return ActionType.IGNORE
        r = self._rng.random() * total
        upto = 0.0
        for action, w in weights.items():
            upto += w
            if r <= upto:
                return action
        return ActionType.IGNORE
