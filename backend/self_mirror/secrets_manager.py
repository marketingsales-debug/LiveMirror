"""
Secrets Management Layer for SelfMirror.
Ensures sensitive environment variables are NEVER exposed to the agent.
"""

import os
from typing import Dict, List, Optional

# List of keys that are STRICTLY PROHIBITED from being seen by the agent
SENSITIVE_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "SELFMIRROR_API_KEY",
    "GITHUB_TOKEN",
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
]

class SecretManager:
    """Handles safe access to environment variables with database overrides."""
    
    @staticmethod
    def get_safe_env() -> Dict[str, str]:
        """
        Returns a filtered dictionary of environment variables.
        Removes all sensitive keys to prevent agent exposure.
        """
        from src.memory.lesson_learnt import LessonLearntStore
        db = LessonLearntStore()
        
        # Start with environment
        safe_env = {}
        for key, value in os.environ.items():
            if not SecretManager.is_sensitive(key):
                safe_env[key] = value
        
        # Override with DB secrets if they are marked as non-sensitive 
        # (Though usually all DB secrets here will be sensitive and thus filtered)
        # The main use case is providing the REAL keys to the backend, not the agent.
        return safe_env

    @staticmethod
    def get_secret(key: str) -> Optional[str]:
        """Get secret from DB or Env."""
        from src.memory.lesson_learnt import LessonLearntStore
        db = LessonLearntStore()
        
        val = db.get_secret(key)
        if val:
            return val
        return os.getenv(key)

    @staticmethod
    def is_sensitive(key: str) -> bool:
        """Check if a key is sensitive."""
        return key.upper() in SENSITIVE_KEYS or any(s in key.upper() for s in ["SECRET", "KEY", "TOKEN", "PASSWORD"])
