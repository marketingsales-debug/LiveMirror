"""Tests for the SecretManager."""

import os
from backend.self_mirror.secrets_manager import SecretManager

def test_is_sensitive():
    assert SecretManager.is_sensitive("OPENAI_API_KEY") is True
    assert SecretManager.is_sensitive("GITHUB_TOKEN") is True
    assert SecretManager.is_sensitive("MY_PASSWORD") is True
    assert SecretManager.is_sensitive("PUBLIC_VAR") is False

def test_get_safe_env():
    # Mock environment
    os.environ["OPENAI_API_KEY"] = "secret-123"
    os.environ["PUBLIC_VAR"] = "public-456"
    os.environ["DB_PASSWORD"] = "password-789"
    
    safe_env = SecretManager.get_safe_env()
    
    assert "OPENAI_API_KEY" not in safe_env
    assert "DB_PASSWORD" not in safe_env
    assert safe_env["PUBLIC_VAR"] == "public-456"
    
    # Cleanup
    del os.environ["OPENAI_API_KEY"]
    del os.environ["PUBLIC_VAR"]
    del os.environ["DB_PASSWORD"]
