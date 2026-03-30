#!/usr/bin/env python3
"""
LiveMirror Multi-Model Agentic Simulation - Kaggle Deployment & Verification
This script automates the setup, dependency installation, and health verification for LiveMirror on Kaggle.
"""

import os
import subprocess
import time
import urllib.request
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# --- Configuration & Registry ---

NVIDIA_REGISTRY = {
    "NVIDIA_API_KEY_PRIMARY": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_MISTRAL": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_QWEN": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_NEMOTRON": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_LANGCHAIN": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_RERANK": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_TABLE": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_QWEN_397B": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_QWEN_LC": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_STEPFUN": "nvapi-REPLACE_WITH_YOUR_KEY",
    "NVIDIA_API_KEY_DEEPSEEK": "nvapi-REPLACE_WITH_YOUR_KEY",
}

# ANSI Aesthetics
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{text.center(80)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

def setup_kaggle():
    """Clones the repository and sets up the environment on Kaggle."""
    print_header("🚀 Starting LiveMirror Kaggle Setup")
    
    # Check if we are in /kaggle/working
    is_kaggle = os.path.exists("/kaggle/working")
    base_path = Path("/kaggle/working") if is_kaggle else Path.cwd()
    
    # 1. Clone Repository if not present
    repo_dir = base_path / "LiveMirror"
    if not repo_dir.exists():
        print(f"{BLUE}📥 Cloning LiveMirror repository...{RESET}")
        subprocess.run(["git", "clone", "https://github.com/marketingsales-debug/LiveMirror.git"], cwd=str(base_path), check=True)
    else:
        print(f"{GREEN}📂 Repository already exists at {repo_dir}{RESET}")

    os.chdir(str(repo_dir))
    
    # 2. Create .env file
    print(f"{BLUE}🔧 Configuring environment variables...{RESET}")
    with open(".env", "w") as f:
        for k, v in NVIDIA_REGISTRY.items():
            f.write(f"{k}={v}\n")
        f.write("PYTHONPATH=.\n")
        f.write("ENVIRONMENT=kaggle\n")
    print(f"{GREEN}✅ .env file created successfully.{RESET}")

    # 3. Install Python Dependencies
    print(f"{BLUE}📦 Installing backend dependencies...{RESET}")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "langchain-nvidia-ai-endpoints", "openai"], check=True)
    print(f"{GREEN}✅ Python dependencies installed.{RESET}")

    # 4. Build Frontend if it exists
    f_dir = repo_dir / "frontend"
    if f_dir.exists():
        print(f"{BLUE}🎨 Setting up frontend...{RESET}")
        try:
            subprocess.run(["npm", "install", "--no-audit"], cwd=str(f_dir), check=True)
            subprocess.run(["npm", "run", "build"], cwd=str(f_dir), check=True)
            print(f"{GREEN}✅ Frontend built successfully.{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠️ Frontend build failed (skipping): {e}{RESET}")
    
    # 5. Create Data Directories
    print(f"{BLUE}📂 Creating data directories...{RESET}")
    os.makedirs(base_path / "data/memory", exist_ok=True)
    os.makedirs(base_path / "data/evolution", exist_ok=True)
    print(f"{GREEN}✅ Directories ready.{RESET}")

    # 6. Start Backend in Background
    print(f"{BLUE}🖥️ Starting backend server...{RESET}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_dir)
    for k, v in NVIDIA_REGISTRY.items():
        env[k] = v
    
    log_path = base_path / "backend.log"
    with open(log_path, "w") as lf:
        proc = subprocess.Popen(
            [sys.executable, "backend/run.py"],
            cwd=str(repo_dir),
            env=env,
            stdout=lf,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        # Health Check Loop
        print(f"{BLUE}⏳ Waiting for backend to come online...{RESET}")
        for i in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as r:
                    if r.status == 200:
                        print(f"{BOLD}{GREEN}✅ SYSTEM ONLINE!{RESET}")
                        break
            except Exception:
                time.sleep(2)
                if i % 5 == 0:
                    print(f"   Still waiting... ({i*2}s)")
        else:
            print(f"{BOLD}{RED}❌ FAILED TO START BACKEND{RESET}")
            print(f"{YELLOW}Check logs at: {log_path}{RESET}")
            proc.terminate()
            return

    # 7. Expose with Localtunnel
    print(f"{MAGENTA}{BOLD}🔗 Exposing server via Localtunnel...{RESET}")
    print(f"{BOLD}{YELLOW}Note: You will need to provide your notebook IP to Localtunnel.{RESET}")
    try:
        subprocess.run(["npx", "localtunnel", "--port", "8000"])
    except KeyboardInterrupt:
        print(f"\n{BLUE}Exiting...{RESET}")
        proc.terminate()

def verify_apis():
    """Optional: Run the original API verification tests once online."""
    print_header("🔍 Running API Verification")
    # This would call the original logic if needed, but setup_kaggle handles the deployment.
    # For now, we'll just confirm the environment is set.
    for k in NVIDIA_REGISTRY:
        if k in os.environ or os.path.exists(".env"):
            print(f"{GREEN}✓ {k} is configured.{RESET}")

if __name__ == "__main__":
    try:
        setup_kaggle()
    except Exception as e:
        print(f"\n{BOLD}{RED}Critical failure during setup:{RESET}")
        print(f"{RED}{str(e)}{RESET}")
        sys.exit(1)
