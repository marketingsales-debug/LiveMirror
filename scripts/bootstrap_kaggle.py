"""
LiveMirror v2.0 - Kaggle Bootstrap Utility.
Headless initialization for notebook environments.
"""

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from socket import timeout as socket_timeout


def wait_for_backend(url: str, process: subprocess.Popen, timeout_seconds: int = 60, interval: int = 2) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=5)
            raise RuntimeError(
                "Backend exited early.\n"
                f"STDOUT:\n{stdout}\n"
                f"STDERR:\n{stderr}"
            )
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    print(f"✅ Backend is responding at {url}")
                    return
                last_error = f"Unexpected status: {response.status}"
        except (urllib.error.URLError, socket_timeout) as exc:
            last_error = str(exc)
        time.sleep(interval)

    raise TimeoutError(f"Backend did not become ready at {url}. Last error: {last_error}")

def setup_kaggle():
    print("🚀 Starting LiveMirror Kaggle Setup...")
    
    # 1. Detect base directory accurately
    # Handle /kaggle/working/LiveMirror vs /kaggle/working/
    curr = Path(os.getcwd())
    if (curr / "LiveMirror").exists():
        base_dir = curr / "LiveMirror"
    elif (curr / "backend").exists() and (curr / "frontend").exists():
        base_dir = curr
    elif (curr.parent / "backend").exists() and (curr.parent / "frontend").exists():
        base_dir = curr.parent
    else:
        # Deep search for backend/run.py
        found = list(curr.glob("**/backend/run.py"))
        if found:
            base_dir = found[0].parent.parent
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
        print(f"📂 Found frontend directory at {frontend_dir}")
        try:
            # Check if npm is available
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
            
            print("  - Running npm install...")
            subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=str(frontend_dir), check=True)
            
            print("  - Running npm run build...")
            subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True)
            
            # Double check dist exists
            dist_path = frontend_dir / "dist"
            if (dist_path / "index.html").exists():
                print(f"✅ Frontend build successful at {dist_path}")
            else:
                print(f"❌ Frontend build failed: {dist_path}/index.html not found.")
                # List files in dist for debugging
                if dist_path.exists():
                    print(f"   Contents of {dist_path}: {os.listdir(dist_path)}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Frontend build process failed: {e}")
        except FileNotFoundError:
            print("❌ npm not found. Skipping frontend build.")
    else:
        print(f"⚠️ Warning: frontend directory NOT found at {frontend_dir}")
        # List current directory to help user
        print(f"   Current directory contains: {os.listdir('.')}")
    
    # 4. Initialize Memory Stores in writable directory
    print("💾 Initializing Memory Stores...")
    os.makedirs("/kaggle/working/data/memory", exist_ok=True)
    os.makedirs("/kaggle/working/data/evolution", exist_ok=True)
    
    # 5. Start Backend in Background
    print("🧠 Launching Reasoning API...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(base_dir)
    
    backend_script = base_dir / "backend" / "run.py"
    if not backend_script.exists():
        print(f"❌ Backend script NOT found at {backend_script}")
        return
    
    # Decouple and start
    # We use a log file to see what's happening
    log_file = open("/kaggle/working/backend.log", "w")
    backend_proc = subprocess.Popen(
        ["python", str(backend_script)],
        cwd=str(base_dir),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True 
    )
    
    # 6. Create Public Tunnel (Wait for boot)
    print("⏳ Waiting for backend to initialize (checking http://127.0.0.1:8000/health)...")
    try:
        wait_for_backend("http://127.0.0.1:8000/health", backend_proc)
    except Exception as e:
        print(f"❌ Backend initialization failed: {e}")
        # Show last few lines of log
        print("\n--- Last 20 lines of backend.log ---")
        try:
            with open("/kaggle/working/backend.log", "r") as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line, end="")
        except:
            pass
        return
    
    print("\n🔗 Creating Public Dashboard Tunnel...")
    print("--- ACCESS LINK BELOW ---")
    
    try:
        # Use --local-host to ensure it binds correctly
        subprocess.run(["npx", "localtunnel", "--port", "8000"], check=False)
    except KeyboardInterrupt:
        print("\n🛑 Tunnel closed by user.")
        backend_proc.terminate()
        log_file.close()

if __name__ == "__main__":
    setup_kaggle()
