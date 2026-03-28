"""
SelfMirror Services — the 'limbs' of the autonomous agent.
Provides safe file I/O and command execution.
"""

import os
import subprocess
from typing import List, Optional
from pathlib import Path

class FileService:
    """Safe read/write operations for the agent."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()

    def _safe_path(self, relative_path: str) -> Path:
        """Ensure path is within the base directory."""
        path = (self.base_path / relative_path).resolve()
        if not str(path).startswith(str(self.base_path)):
            raise PermissionError(f"Access denied: {relative_path} is outside the workspace.")
        return path

    def read_file(self, file_path: str) -> str:
        """Read a file's content."""
        full_path = self._safe_path(file_path)
        if not full_path.exists():
            return f"Error: File {file_path} does not exist."
        return full_path.read_text(encoding="utf-8")

    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file (creates parents if needed)."""
        full_path = self._safe_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return True

    def list_files(self, directory: str = ".") -> List[str]:
        """List all files in a directory."""
        full_path = self._safe_path(directory)
        files = []
        for root, _, filenames in os.walk(full_path):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), self.base_path)
                if ".git" not in rel and "__pycache__" not in rel:
                    files.append(rel)
        return sorted(files)


class ExecutionService:
    """Run shell commands and capture output."""

    def __init__(self, cwd: str):
        self.cwd = cwd

    def run_command(self, command: str) -> dict:
        """Execute a command and return stdout/stderr."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=60  # Safety timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "Command timed out (60s limit).", "exit_code": -1}
        except Exception as e:
            return {"success": False, "stderr": str(e), "exit_code": -1}
