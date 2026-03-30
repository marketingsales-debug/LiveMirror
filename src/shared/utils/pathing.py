"""
Unified Pathing Utility.
Detects environment (Kaggle vs. Cloud) and sets writable paths accordingly.
"""

import os
from pathlib import Path

def is_kaggle() -> bool:
    """Detects if we are running in a Kaggle notebook environment."""
    return os.path.exists('/kaggle/working')

def get_workspace_root() -> Path:
    """Returns the base writable directory for the current environment."""
    if is_kaggle():
        return Path('/kaggle/working')
    # Standard Linux / Oracle Cloud
    return Path(os.getcwd())

def get_data_dir() -> Path:
    """Returns the directory for persistent data (SQLite, Logs)."""
    root = get_workspace_root()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_env_file() -> Path:
    """Returns the path to the .env file."""
    # In Kaggle, we often pass secrets via User Secrets, not a .env file
    return get_workspace_root() / ".env"
