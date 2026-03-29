import time
import pytest
from backend.self_mirror.security import validate_command
from backend.self_mirror.services import HostExecutionService

def test_redos_vulnerability():
    """Test if the validate_command regexes are vulnerable to ReDoS."""
    start_time = time.time()
    # A long string with many spaces and repetitive patterns
    malicious_cmd = "git " + " ".join(["push" for _ in range(10000)])
    result = validate_command(malicious_cmd)
    end_time = time.time()
    
    assert result["allowed"] is False
    assert (end_time - start_time) < 0.5, f"Regex took too long: {end_time - start_time}s (ReDoS possible)"

def test_resource_exhaustion():
    """Test if the resource limits prevent a CPU/Memory hang."""
    es = HostExecutionService(".", timeout=2)
    start_time = time.time()
    # Trying to execute an allowed command but with a sleep or infinite loop if we could.
    # Since python -c is blocked, let's just test the timeout on an allowed command that might hang.
    # We can use `find /` which is allowed and takes a long time.
    result = es.run_command("find / -name '*.py'")
    end_time = time.time()
    
    assert (end_time - start_time) < 3.0, "Timeout or resource limit failed!"

if __name__ == "__main__":
    test_redos_vulnerability()
    test_resource_exhaustion()
    print("Stress test passed successfully.")
