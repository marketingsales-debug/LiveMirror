"""
SelfMirror Services — the 'limbs' of the autonomous agent.
Provides safe file I/O and sandboxed command execution.
"""

import os
import shlex
import subprocess
from typing import List, Optional
from pathlib import Path

# Note: 'resource' is Unix-only.
try:
    import resource
except ImportError:
    resource = None

from .security import validate_command

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

    def backup_file(self, file_path: str) -> Optional[str]:
        """Create a temporary backup of a file. Returns backup path relative to base."""
        full_path = self._safe_path(file_path)
        if not full_path.exists():
            return None
        backup_path = full_path.with_suffix(full_path.suffix + ".bak")
        backup_path.write_text(full_path.read_text(encoding="utf-8"), encoding="utf-8")
        return os.path.relpath(backup_path, self.base_path)

    def restore_file(self, file_path: str) -> bool:
        """Restore a file from its backup and delete the backup."""
        full_path = self._safe_path(file_path)
        backup_path = full_path.with_suffix(full_path.suffix + ".bak")
        if not backup_path.exists():
            return False
        full_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
        backup_path.unlink()
        return True

    def delete_backup(self, file_path: str) -> bool:
        """Delete the backup file without restoring."""
        full_path = self._safe_path(file_path)
        backup_path = full_path.with_suffix(full_path.suffix + ".bak")
        if backup_path.exists():
            backup_path.unlink()
            return True
        return False


    def list_files(self, directory: str = ".") -> List[str]:
        """List all files in a directory."""
        full_path = self._safe_path(directory)
        files = []
        for root, _, filenames in os.walk(full_path):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), self.base_path)
                skip = (".git", "__pycache__", "node_modules", ".venv", ".pytest_cache")
                if not any(s in rel for s in skip):
                    files.append(rel)
        return sorted(files)


class ExecutionService:
    """Sandboxed command execution with allowlist enforcement and resource limits."""

    def __init__(self, cwd: str, timeout: int = 120):
        self.cwd = cwd
        self.timeout = timeout
        # Limits: 4GB memory, 60s CPU (per process)
        self.mem_limit = 4 * 1024 * 1024 * 1024
        self.cpu_limit = 60

    def _set_resource_limits(self):
        """Pre-execution function to set resource limits for the sub-process."""
        if resource:
            try:
                # CPU time limit (seconds)
                resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_limit, self.cpu_limit + 5))
                # Address space limit (bytes)
                # Some OSs (like macOS) have strict limits on RLIMIT_AS, we try but don't crash if it fails
                resource.setrlimit(resource.RLIMIT_AS, (self.mem_limit, self.mem_limit))
                # Memory limit (bytes)
                resource.setrlimit(resource.RLIMIT_RSS, (self.mem_limit, self.mem_limit))
            except Exception:
                pass 

    def run_command(self, command: str) -> dict:
        """Execute a command after validating against the allowlist and setting resource limits."""
        # 1. Validate before executing
        check = validate_command(command)
        if not check["allowed"]:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"BLOCKED: {check['reason']}",
                "exit_code": -1,
            }

        # 2. Execute using shlex split (no shell=True)
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                preexec_fn=self._set_resource_limits,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:],  # cap output size
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out ({self.timeout}s limit).",
                "exit_code": -1,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}
