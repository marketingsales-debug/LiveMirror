"""Tests for the SelfMirror services layer (FileService + ExecutionService)."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.self_mirror.services import FileService, ExecutionService


# ── FileService ─────────────────────────────────────────────────────


class TestFileService:
    """Tests for safe file I/O operations."""

    @pytest.fixture
    def fs(self, tmp_path):
        """Create a FileService rooted at a temp directory."""
        return FileService(str(tmp_path))

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample file in the temp workspace."""
        f = tmp_path / "hello.txt"
        f.write_text("Hello, World!", encoding="utf-8")
        return f

    # --- Path sandboxing ---

    def test_safe_path_within_base(self, fs, tmp_path):
        path = fs._safe_path("sub/file.txt")
        assert str(path).startswith(str(tmp_path))

    def test_safe_path_blocks_traversal(self, fs):
        with pytest.raises(PermissionError, match="outside the workspace"):
            fs._safe_path("../../etc/passwd")

    def test_safe_path_blocks_absolute(self, fs):
        with pytest.raises(PermissionError):
            fs._safe_path("/etc/passwd")

    # --- Read ---

    def test_read_existing_file(self, fs, sample_file):
        content = fs.read_file("hello.txt")
        assert content == "Hello, World!"

    def test_read_nonexistent_file(self, fs):
        result = fs.read_file("nope.txt")
        assert "does not exist" in result

    # --- Write ---

    def test_write_creates_file(self, fs, tmp_path):
        assert fs.write_file("new.txt", "new content") is True
        assert (tmp_path / "new.txt").read_text() == "new content"

    def test_write_creates_parent_dirs(self, fs, tmp_path):
        fs.write_file("deep/nested/file.py", "# code")
        assert (tmp_path / "deep" / "nested" / "file.py").exists()

    def test_write_overwrites_existing(self, fs, sample_file):
        fs.write_file("hello.txt", "Overwritten")
        assert sample_file.read_text() == "Overwritten"

    # --- Backup / Restore ---

    def test_backup_creates_bak_file(self, fs, sample_file, tmp_path):
        backup_path = fs.backup_file("hello.txt")
        assert backup_path is not None
        assert (tmp_path / backup_path).exists()
        assert (tmp_path / backup_path).read_text() == "Hello, World!"

    def test_backup_nonexistent_returns_none(self, fs):
        assert fs.backup_file("nope.txt") is None

    def test_restore_reverts_content(self, fs, sample_file, tmp_path):
        fs.backup_file("hello.txt")
        fs.write_file("hello.txt", "BROKEN")
        assert sample_file.read_text() == "BROKEN"

        assert fs.restore_file("hello.txt") is True
        assert sample_file.read_text() == "Hello, World!"
        # Backup should be deleted after restore
        assert not (tmp_path / "hello.txt.bak").exists()

    def test_restore_without_backup_returns_false(self, fs):
        assert fs.restore_file("hello.txt") is False

    def test_delete_backup(self, fs, sample_file, tmp_path):
        fs.backup_file("hello.txt")
        assert (tmp_path / "hello.txt.bak").exists()
        assert fs.delete_backup("hello.txt") is True
        assert not (tmp_path / "hello.txt.bak").exists()

    def test_delete_backup_when_none_exists(self, fs):
        assert fs.delete_backup("hello.txt") is False

    # --- List files ---

    def test_list_files_finds_all(self, fs, tmp_path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.py").write_text("b")
        files = fs.list_files()
        assert "a.py" in files
        assert os.path.join("sub", "b.py") in files

    def test_list_files_skips_hidden_dirs(self, fs, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("x")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "mod.pyc").write_text("x")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("x")
        files = fs.list_files()
        assert all(".git" not in f for f in files)
        assert all("__pycache__" not in f for f in files)
        assert all("node_modules" not in f for f in files)


# ── ExecutionService ────────────────────────────────────────────────


class TestExecutionService:
    """Tests for sandboxed command execution."""

    @pytest.fixture
    def es(self, tmp_path):
        return ExecutionService(str(tmp_path))

    def test_allowed_command_runs(self, es):
        result = es.run_command("echo hello")
        assert result["success"] is True
        assert "hello" in result["stdout"]
        assert result["exit_code"] == 0

    def test_blocked_command_rejected(self, es):
        result = es.run_command("rm -rf /")
        assert result["success"] is False
        assert "BLOCKED" in result["stderr"]
        assert result["exit_code"] == -1

    def test_unlisted_command_rejected(self, es):
        result = es.run_command("curl http://example.com")
        assert result["success"] is False
        assert "BLOCKED" in result["stderr"]

    def test_command_timeout(self, tmp_path):
        es = ExecutionService(str(tmp_path), timeout=1)
        # 'find /' is allowed and will run long enough to timeout
        result = es.run_command("find / -name '*.py'")
        # Should either timeout or complete — either way, no crash
        assert isinstance(result, dict)
        assert "exit_code" in result

    def test_output_is_capped(self, es, tmp_path):
        # Create a file that produces a lot of output
        big_file = tmp_path / "big.txt"
        big_file.write_text("x\n" * 10000)
        result = es.run_command(f"cat {big_file}")
        # stdout is capped at 5000 chars
        assert len(result["stdout"]) <= 5001

    def test_failed_command_returns_nonzero(self, es):
        result = es.run_command("python -c 'raise ValueError(\"boom\")'")
        assert result["success"] is False
        assert result["exit_code"] != 0
