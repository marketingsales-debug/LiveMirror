"""
LiveMirror v2.0 - Kaggle Bootstrap Utility.
Headless initialization for notebook environments.
"""

import os
import subprocess
import time
from pathlib import Path

def setup_kaggle():
    print("🚀 Starting LiveMirror Kaggle Setup...")
    
    # 1. Detect base directory
    base_dir = Path(os.getcwd())
    print(f"📍 Working Directory: {base_dir}")
    
    # 2. Install Python dependencies
    print("📦 Installing Python dependencies...")
    req_path = base_dir / "backend" / "requirements.txt"
    if req_path.exists():
        subprocess.run(["pip", "install", "-r", str(req_path)], check=True)
    
    # 3. Build Frontend (Required for Dashboard serving)
    print("🎨 Building Frontend Dashboard...")
    frontend_dir = base_dir / "frontend"
    if frontend_dir.exists():
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)
        subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True)
    else:
        print("⚠️ Warning: frontend directory not found. Dashboard will be unavailable.")
    
    # 4. Initialize Memory Stores in writable directory
    print("💾 Initializing Memory Stores...")
    os.makedirs("/kaggle/working/data/memory", exist_ok=True)
    os.makedirs("/kaggle/working/data/evolution", exist_ok=True)
    
    # 5. Start Backend in Background
    print("🧠 Launching Reasoning API...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base_dir)
    
    backend_script = base_dir / "backend" / "run.py"
    
    # Using start_new_session to decouple the process
    backend_proc = subprocess.Popen(
        ["python", str(backend_script)],
        cwd=str(base_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True 
    )
    
    # 6. Create Public Tunnel (Wait for boot)
    print("⏳ Waiting for backend to initialize (15s)...")
    time.sleep(15)
    
    print("\n🔗 Creating Public Dashboard Tunnel...")
    print("--- ACCESS LINK BELOW ---")
    
    try:
        subprocess.run(["npx", "localtunnel", "--port", "8000"], check=False)
    except KeyboardInterrupt:
        print("\n🛑 Tunnel closed by user.")
        backend_proc.terminate()

if __name__ == "__main__":
    setup_kaggle()
