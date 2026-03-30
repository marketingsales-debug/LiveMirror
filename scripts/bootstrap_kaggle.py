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
    
    # 1. Detect base directory accurately
    # Handle nested LiveMirror/LiveMirror if user cloned incorrectly
    curr = Path(os.getcwd())
    if (curr / "LiveMirror").exists():
        base_dir = curr / "LiveMirror"
    else:
        base_dir = curr
        
    print(f"📍 Base Directory Detected: {base_dir}")
    os.chdir(str(base_dir))
    
    # 2. Install Python dependencies
    print("📦 Installing Python dependencies...")
    req_path = base_dir / "backend" / "requirements.txt"
    if req_path.exists():
        subprocess.run(["pip", "install", "-r", str(req_path)], check=True)
    
    # 3. Build Frontend (Required for Dashboard serving)
    print("🎨 Building Frontend Dashboard...")
    frontend_dir = base_dir / "frontend"
    if frontend_dir.exists():
        # Install and build
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)
        subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True)
        
        # Double check dist exists
        dist_path = frontend_dir / "dist"
        if (dist_path / "index.html").exists():
            print(f"✅ Frontend build successful at {dist_path}")
        else:
            print("❌ Frontend build failed to produce index.html")
    else:
        print("⚠️ Warning: frontend directory not found.")
    
    # 4. Initialize Memory Stores in writable directory
    print("💾 Initializing Memory Stores...")
    os.makedirs("/kaggle/working/data/memory", exist_ok=True)
    os.makedirs("/kaggle/working/data/evolution", exist_ok=True)
    
    # 5. Start Backend in Background
    print("🧠 Launching Reasoning API...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base_dir)
    
    backend_script = base_dir / "backend" / "run.py"
    
    # Decouple and start
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
    print("⏳ Waiting for backend to initialize (20s)...")
    time.sleep(20)
    
    print("\n🔗 Creating Public Dashboard Tunnel...")
    print("--- ACCESS LINK BELOW ---")
    
    try:
        subprocess.run(["npx", "localtunnel", "--port", "8000"], check=False)
    except KeyboardInterrupt:
        print("\n🛑 Tunnel closed by user.")
        backend_proc.terminate()

if __name__ == "__main__":
    setup_kaggle()
