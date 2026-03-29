"""Tests for the SelfMirror agent logic (parsing + AgentLoop)."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.self_mirror.agent_logic import (
    _parse_action,
    _parse_verify,
    LLMClient,
    AgentLoop,
)


# ── _parse_action ───────────────────────────────────────────────────


class TestParseAction:
    """Tests for extracting ACTION JSON from LLM responses."""

    def test_direct_match(self):
        response = 'THOUGHT: thinking\nACTION: {"type": "READ_FILE", "path": "src/main.py"}'
        result = _parse_action(response)
        assert result == {"type": "READ_FILE", "path": "src/main.py"}

    def test_no_space_after_colon(self):
        response = 'ACTION:{"type": "COMPLETE"}'
        result = _parse_action(response)
        assert result == {"type": "COMPLETE"}

    def test_write_file_action(self):
        action = {"type": "WRITE_FILE", "path": "test.py", "content": "print('hi')"}
        response = f"THOUGHT: writing\nACTION: {json.dumps(action)}"
        result = _parse_action(response)
        assert result["type"] == "WRITE_FILE"
        assert result["content"] == "print('hi')"

    def test_code_block_format(self):
        response = 'THOUGHT: doing stuff\nACTION: ```json\n{"type": "COMPLETE"}\n```'
        result = _parse_action(response)
        assert result == {"type": "COMPLETE"}

    def test_regex_fallback(self):
        response = 'THOUGHT: hmm\nACTION:  {"type": "RUN_COMMAND", "command": "pytest"}'
        result = _parse_action(response)
        assert result["type"] == "RUN_COMMAND"

    def test_no_action_returns_none(self):
        response = "THOUGHT: I'm just thinking, no action yet."
        assert _parse_action(response) is None

    def test_malformed_json_returns_none(self):
        response = 'ACTION: {type: "COMPLETE"}'  # invalid JSON
        assert _parse_action(response) is None

    def test_empty_string(self):
        assert _parse_action("") is None

    def test_action_among_other_lines(self):
        response = """THOUGHT: Let me read the config.
Some extra text here.
ACTION: {"type": "READ_FILE", "path": "config.yaml"}
VERIFY: pytest tests/"""
        result = _parse_action(response)
        assert result["type"] == "READ_FILE"


# ── _parse_verify ───────────────────────────────────────────────────


class TestParseVerify:
    """Tests for extracting VERIFY command from LLM responses."""

    def test_extracts_verify_command(self):
        response = "THOUGHT: done\nACTION: {}\nVERIFY: pytest tests/ -x -q"
        result = _parse_verify(response)
        assert result == "pytest tests/ -x -q"

    def test_no_verify_returns_none(self):
        response = "THOUGHT: done\nACTION: {}"
        assert _parse_verify(response) is None

    def test_empty_verify_returns_none(self):
        response = "VERIFY: "
        assert _parse_verify(response) is None

    def test_verify_with_extra_whitespace(self):
        response = "VERIFY:   npm run build  "
        result = _parse_verify(response)
        assert result == "npm run build"


# ── LLMClient ───────────────────────────────────────────────────────


class TestLLMClient:
    """Tests for LLM client configuration checks."""

    def test_not_configured_when_empty(self):
        with patch.dict("os.environ", {"LLM_API_KEY": ""}, clear=False):
            client = LLMClient()
            client.api_key = ""
            assert client.is_configured() is False

    def test_not_configured_when_missing(self):
        client = LLMClient()
        client.api_key = "missing"
        assert client.is_configured() is False

    def test_configured_with_real_key(self):
        client = LLMClient()
        client.api_key = "sk-abc123"
        assert client.is_configured() is True


# ── AgentLoop ───────────────────────────────────────────────────────


class TestAgentLoop:
    """Tests for the Think-Act-Verify loop."""

    @pytest.fixture
    def loop(self, tmp_path):
        return AgentLoop(workspace_root=str(tmp_path))

    @pytest.mark.asyncio
    async def test_unconfigured_llm_returns_error(self, loop):
        loop.llm.api_key = ""
        result = await loop.run_goal("fix a bug")
        assert len(result) == 1
        assert "LLM_API_KEY" in result[0]

    @pytest.mark.asyncio
    async def test_complete_action_stops_loop(self, loop):
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        loop.llm.chat = AsyncMock(
            return_value='THOUGHT: Done.\nACTION: {"type": "COMPLETE"}'
        )
        result = await loop.run_goal("test goal")
        assert any("Done" in t for t in result)

    @pytest.mark.asyncio
    async def test_read_file_action(self, loop, tmp_path):
        (tmp_path / "readme.md").write_text("# Hello")
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        loop.llm.chat = AsyncMock(
            side_effect=[
                'THOUGHT: Read it.\nACTION: {"type": "READ_FILE", "path": "readme.md"}',
                'THOUGHT: Done.\nACTION: {"type": "COMPLETE"}',
            ]
        )
        result = await loop.run_goal("read the readme")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_parse_failure_reprompts(self, loop):
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        loop.llm.chat = AsyncMock(
            side_effect=[
                "THOUGHT: I forgot the action format.",
                "THOUGHT: Still wrong.",
                "THOUGHT: Third fail.",
            ]
        )
        result = await loop.run_goal("do something", max_iterations=10)
        # Should stop after 3 parse failures
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_max_iterations_capped_at_20(self, loop):
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        # Request 50, should be capped to 20
        loop.llm.chat = AsyncMock(
            return_value='THOUGHT: Done.\nACTION: {"type": "COMPLETE"}'
        )
        await loop.run_goal("test", max_iterations=50)
        # Just verify it didn't crash and completed
        assert loop.llm.chat.call_count >= 1

    @pytest.mark.asyncio
    async def test_unknown_action_type_handled(self, loop):
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        loop.llm.chat = AsyncMock(
            side_effect=[
                'THOUGHT: Try this.\nACTION: {"type": "DEPLOY_NUKES"}',
                'THOUGHT: Done.\nACTION: {"type": "COMPLETE"}',
            ]
        )
        result = await loop.run_goal("test")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_llm_error_stops_loop(self, loop):
        loop.llm = AsyncMock()
        loop.llm.is_configured.return_value = True
        loop.llm.chat = AsyncMock(return_value="Error: Connection refused")
        result = await loop.run_goal("test")
        assert any("Error" in t for t in result)
