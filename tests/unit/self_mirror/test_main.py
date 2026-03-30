"""Tests for the SelfMirror API router."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.self_mirror.main import router

# Setup a test app
app = FastAPI()
app.include_router(router)
API_KEY = "test-key"
AUTH_HEADERS = {"X-API-Key": API_KEY}

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_list_files_success():
    """Test the /files endpoint."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        mock_instance = MockLoop.return_value
        mock_instance.files.list_files.return_value = ["file1.py", "file2.py"]
        
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/files", headers=AUTH_HEADERS)
                
    assert response.status_code == 200
    assert response.json() == {"files": ["file1.py", "file2.py"]}
    MockLoop.assert_called_once() # Should be instantiated per request

@pytest.mark.anyio
async def test_run_command_success():
    """Test the /exec endpoint."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        mock_instance = MockLoop.return_value
        mock_instance.exec.run_command.return_value = {
            "success": True, 
            "stdout": "hello", 
            "stderr": "", 
            "exit_code": 0
        }
        
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/exec", json={"command": "echo hello"}, headers=AUTH_HEADERS)
                
    assert response.status_code == 200
    assert response.json()["stdout"] == "hello"
    MockLoop.assert_called_once()

@pytest.mark.anyio
async def test_start_goal_success():
    """Test the /goal endpoint."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        mock_instance = MockLoop.return_value
        mock_instance.run_goal = AsyncMock(return_value=["Thought 1", "Thought 2"])
        
        goal_data = {
            "goal": "Fix everything",
            "context_files": ["main.py"],
            "max_iterations": 5
        }
        
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/goal", json=goal_data, headers=AUTH_HEADERS)
                
    assert response.status_code == 200
    assert response.json()["thoughts"] == ["Thought 1", "Thought 2"]
    assert response.json()["status"] == "completed"
    MockLoop.assert_called_once()
    mock_instance.run_goal.assert_called_with("Fix everything", ["main.py"], max_iterations=5)

@pytest.mark.anyio
async def test_api_error_handling():
    """Test that exceptions are caught and returned as 500."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        mock_instance = MockLoop.return_value
        mock_instance.files.list_files.side_effect = Exception("System crash")
        
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/files", headers=AUTH_HEADERS)
                
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to list files."


@pytest.mark.anyio
async def test_exec_rejects_shell_substitution():
    """Reject command substitution/backticks at validation."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/exec", json={"command": "echo $(whoami)"}, headers=AUTH_HEADERS)

    assert response.status_code == 422
    MockLoop.assert_not_called()


@pytest.mark.anyio
async def test_goal_rejects_invalid_context_path():
    """Reject context files with path traversal."""
    with patch("backend.self_mirror.main.AgentLoop") as MockLoop:
        with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/goal",
                    json={"goal": "Fix it", "context_files": ["../secret.txt"], "max_iterations": 3},
                    headers=AUTH_HEADERS,
                )

    assert response.status_code == 422
    MockLoop.assert_not_called()


@pytest.mark.anyio
async def test_secret_rejects_blank_value():
    """Reject secrets that are only whitespace."""
    with patch.dict(os.environ, {"SELFMIRROR_API_KEY": API_KEY}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/secrets",
                json={"name": "TEST_SECRET", "value": "   "},
                headers=AUTH_HEADERS,
            )

    assert response.status_code == 422
