"""
SelfMirror Services — the 'limbs' of the autonomous agent.
Provides safe file I/O and sandboxed command execution.
Now with Containerization support (Priority 1).
"""

import os
import shlex
import subprocess
from typing import List, Optional, Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod

# Note: 'resource' is Unix-only.
try:
    import resource
except ImportError:
    resource = None

from .security import validate_command
from .secrets_manager import SecretManager

class FileService:
    """Safe read/write operations for the agent."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()

    def _safe_path(self, relative_path: str) -> Path:
        """Ensure path is within the base directory and not a sensitive file."""
        # Prevent access to extremely sensitive files even within workspace
        blocked = [".env", ".git/", "config/secrets", "backend/app/.env"]
        if any(b in relative_path for b in blocked):
            raise PermissionError(f"Access denied: {relative_path} is a protected system file.")

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
        base_path_str = str(self.base_path)
        for root, dirnames, filenames in os.walk(full_path, followlinks=False):
            root_path = Path(root)
            safe_dirnames = []
            for dirname in dirnames:
                candidate = root_path / dirname
                if candidate.is_symlink():
                    continue
                try:
                    resolved = candidate.resolve()
                except FileNotFoundError:
                    continue
                if not str(resolved).startswith(base_path_str):
                    continue
                safe_dirnames.append(dirname)
            dirnames[:] = safe_dirnames
            for f in filenames:
                file_path = root_path / f
                if file_path.is_symlink():
                    continue
                try:
                    resolved = file_path.resolve()
                except FileNotFoundError:
                    continue
                if not str(resolved).startswith(base_path_str):
                    continue
                rel = os.path.relpath(str(resolved), self.base_path)
                skip = (".git", "__pycache__", "node_modules", ".venv", ".pytest_cache")
                if not any(s in rel for s in skip):
                    files.append(rel)
        return sorted(files)


class ExecutionService(ABC):
    """Abstract base class for command execution."""
    @abstractmethod
    def run_command(self, command: str) -> Dict[str, Any]:
        pass


class HostExecutionService(ExecutionService):
    """Host-level command execution with resource limits and allowlist."""

    def __init__(self, cwd: str, timeout: int = 120):
        self.cwd = cwd
        self.timeout = timeout
        self.mem_limit = 4 * 1024 * 1024 * 1024
        self.cpu_limit = 60

    def _set_resource_limits(self):
        if resource:
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_limit, self.cpu_limit + 5))
                resource.setrlimit(resource.RLIMIT_AS, (self.mem_limit, self.mem_limit))
                resource.setrlimit(resource.RLIMIT_RSS, (self.mem_limit, self.mem_limit))
            except Exception:
                pass 

    def run_command(self, command: str) -> Dict[str, Any]:
        check = validate_command(command)
        if not check["allowed"]:
            return {"success": False, "stdout": "", "stderr": f"BLOCKED: {check['reason']}", "exit_code": -1}

        try:
            args = shlex.split(command)
            safe_env = SecretManager.get_safe_env()
            result = subprocess.run(
                args, cwd=self.cwd, capture_output=True, text=True,
                timeout=self.timeout, preexec_fn=self._set_resource_limits, env=safe_env,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Command timed out ({self.timeout}s limit).", "exit_code": -1}
        except Exception:
            return {"success": False, "stdout": "", "stderr": "Command execution failed.", "exit_code": -1}


class ContainerExecutionService(ExecutionService):
    """Docker-based command execution for maximum isolation."""

    def __init__(self, cwd: str, image: str = "python:3.11-slim", timeout: int = 120):
        self.cwd = cwd
        self.image = image
        self.timeout = timeout

    def check_availability(self) -> bool:
        """Verify Docker is running and the image is available."""
        try:
            # Check if docker daemon is running
            subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=5)
            # Check if image exists (pull if not)
            subprocess.run(["docker", "pull", self.image], capture_output=True, check=True, timeout=60)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def run_command(self, command: str) -> Dict[str, Any]:
        """Runs the command inside an ephemeral Docker container."""
        check = validate_command(command)
        if not check["allowed"]:
            return {"success": False, "stdout": "", "stderr": f"BLOCKED: {check['reason']}", "exit_code": -1}

        # Construct Docker command
        # Mounting the workspace as a volume
        abs_cwd = os.path.abspath(self.cwd)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{abs_cwd}:/workspace",
            "-w", "/workspace",
            "--network", "none", # Total network isolation
            "--memory", "4g",
            "--cpus", "1.0",
            self.image,
            "sh", "-c", command
        ]

        try:
            # Note: We still use safe_env but Docker is the primary barrier
            safe_env = SecretManager.get_safe_env()
            result = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=self.timeout, env=safe_env
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Docker command timed out.", "exit_code": -1}
        except Exception:
            return {"success": False, "stdout": "", "stderr": "Docker command failed.", "exit_code": -1}


def get_execution_service(cwd: str, timeout: int = 120) -> ExecutionService:
    """Factory to return the appropriate execution service."""
    mode = os.getenv("SELFMIRROR_EXECUTION_MODE", "host").lower()
    if mode == "docker":
        svc = ContainerExecutionService(cwd=cwd, timeout=timeout)
        if svc.check_availability():
            return svc
        # Fallback to host if docker is not healthy/installed
        return HostExecutionService(cwd=cwd, timeout=timeout)
    return HostExecutionService(cwd=cwd, timeout=timeout)
