"""
Secrets Management Layer for SelfMirror.
Ensures sensitive environment variables are NEVER exposed to the agent.
"""

import os
from typing import Dict, List

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
    """Handles safe access to environment variables."""
    
    @staticmethod
    def get_safe_env() -> Dict[str, str]:
        """
        Returns a filtered dictionary of environment variables.
        Removes all sensitive keys to prevent agent exposure.
        """
        safe_env = {}
        for key, value in os.environ.items():
            if key not in SENSITIVE_KEYS and not any(s in key.upper() for s in ["SECRET", "KEY", "TOKEN", "PASSWORD"]):
                safe_env[key] = value
        return safe_env

    @staticmethod
    def is_sensitive(key: str) -> bool:
        """Check if a key is sensitive."""
        return key.upper() in SENSITIVE_KEYS or any(s in key.upper() for s in ["SECRET", "KEY", "TOKEN", "PASSWORD"])
