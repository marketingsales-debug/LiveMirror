import os
import subprocess
import time
import urllib.request
import sys
from pathlib import Path

# --- Configuration & Registry ---

NVIDIA_REGISTRY = {
    "NVIDIA_API_KEY_PRIMARY": "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",
    "NVIDIA_API_KEY_MISTRAL": "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",
    "NVIDIA_API_KEY_QWEN": "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",
    "NVIDIA_API_KEY_NEMOTRON": "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",
    "NVIDIA_API_KEY_LANGCHAIN": "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",
    "NVIDIA_API_KEY_RERANK": "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",
    "NVIDIA_API_KEY_TABLE": "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",
    "NVIDIA_API_KEY_QWEN_397B": "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",
    "NVIDIA_API_KEY_QWEN_LC": "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",
    "NVIDIA_API_KEY_STEPFUN": "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",
    "NVIDIA_API_KEY_DEEPSEEK": "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",
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
    print_header("🚀 Starting LiveMirror Full NVIDIA Setup")
    
    # 1. Setup Base Directory
    curr = Path(os.getcwd())
    if (curr / "backend").exists() and (curr / "scripts").exists():
        base_dir = curr
    elif (curr / "LiveMirror" / "backend").exists():
        base_dir = curr / "LiveMirror"
    else:
        # Clone if not present
        print(f"{BLUE}📥 Cloning repository...{RESET}")
        subprocess.run(["git", "clone", "https://github.com/marketingsales-debug/LiveMirror.git"], check=True)
        base_dir = curr / "LiveMirror"
        
    print(f"{GREEN}📍 Project Root: {base_dir}{RESET}")
    os.chdir(str(base_dir))
    
    # 2. Inject .env with all keys
    print(f"{BLUE}🔐 Generating .env with all 11+ NVIDIA keys...{RESET}")
    with open(".env", "w") as f:
        for k, v in NVIDIA_REGISTRY.items():
            f.write(f"{k}={v}\n")
        # Critical: Use absolute paths for PYTHONPATH to avoid module errors
        f.write(f"PYTHONPATH={base_dir}:{base_dir}/backend\n")
        f.write("ENVIRONMENT=kaggle\n")
        # Default models for each tier
        f.write("REASONING_MODEL=deepseek-ai/deepseek-v3.2\n")
        f.write("BALANCED_MODEL=qwen/qwen3.5-122b-a10b\n")
        f.write("FLASH_MODEL=stepfun-ai/step-3.5-flash\n")
    print(f"{GREEN}✅ .env file created.{RESET}")
    
    # 3. Install Requirements
    print(f"{BLUE}📦 Installing backend requirements...{RESET}")
    req_path = base_dir / "backend" / "requirements.txt"
    if req_path.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "langchain-nvidia-ai-endpoints", "openai", "python-dotenv", "uvicorn"], check=True)
    print(f"{GREEN}✅ Dependencies installed.{RESET}")
    
    # 4. Build Frontend Dashboard
    print(f"{BLUE}🎨 Rebuilding frontend dashboard to apply hotfixes...{RESET}")
    frontend_dir = base_dir / "frontend"
    if frontend_dir.exists():
        # Ensure node_modules exists or install
        if not (frontend_dir / "node_modules").exists():
            subprocess.run(["npm", "install", "--no-audit"], cwd=str(frontend_dir), check=True)
        subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True)
        print(f"{GREEN}✅ Frontend rebuild completed.{RESET}")
    
    # 5. Initialize Persistence
    print(f"{BLUE}📂 Initializing persistence layers...{RESET}")
    os.makedirs("/kaggle/working/data/memory", exist_ok=True)
    os.makedirs("/kaggle/working/data/evolution", exist_ok=True)
    print(f"{GREEN}✅ Directories created.{RESET}")
    
    # 6. Start Autonomous Backend
    print_header("🧠 Starting LiveMirror Backend")
    env = os.environ.copy()
    # Ensure PYTHONPATH includes project root and backend for module resolution
    env["PYTHONPATH"] = f"{base_dir}:{base_dir}/backend"
    for k, v in NVIDIA_REGISTRY.items():
        env[k] = v

    # Launch in background and write to log
    log_path = "/kaggle/working/backend.log"
    backend_script = base_dir / "backend" / "run.py"
    
    if not backend_script.exists():
        print(f"{RED}❌ Error: {backend_script} not found!{RESET}")
        return

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            [sys.executable, str(backend_script)],
            cwd=str(base_dir),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        # 7. Health Check Verification
        print(f"{BLUE}⏳ Waiting for health check (8000)...{RESET}")
        ready = False
        for i in range(45): # Increased wait time for Kaggle
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as r:
                    if r.status == 200:
                        print(f"{BOLD}{GREEN}✅ LiveMirror is ONLINE and fully integrated!{RESET}")
                        ready = True
                        break
            except:
                if i % 5 == 0: print(f"   ...initializing engine ({i*2}s)")
                time.sleep(2)
        
        if not ready:
            print(f"{BOLD}{RED}❌ FAILED to start. Last logs from backend.log:{RESET}")
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    print(f.read())
            proc.terminate()
            return

        # 8. Start Public Tunnel
        print(f"\n{MAGENTA}{BOLD}🔗 ACCESS LINK BELOW:{RESET}")
        print(f"{YELLOW}Wait for 'your url is' to appear. If you see 'Bad Gateway', refresh in 10s.{RESET}")
        subprocess.run(["npx", "localtunnel", "--port", "8000"])

if __name__ == "__main__":
    setup_kaggle()
