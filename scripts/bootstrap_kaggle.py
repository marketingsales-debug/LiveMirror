"""
LiveMirror v2.0 - Kaggle Bootstrap Utility.
Headless initialization for notebook environments.
"""

import os
import subprocess
import time

def setup_kaggle():
    print("🚀 Starting LiveMirror Kaggle Setup...")
    
    # 1. Install critical dependencies
    print("📦 Installing dependencies...")
    subprocess.run(["pip", "install", "-r", "backend/requirements.txt"], check=True)
    subprocess.run(["pip", "install", "localtunnel"], check=True)
    
    # 2. Start Redis (Simulated for Kaggle)
    # We use a background process or assume local sqlite fallback
    print("💾 Initializing Memory Stores...")
    os.makedirs("/kaggle/working/data/memory", exist_ok=True)
    
    # 3. Start Backend in Background
    print("🧠 Launching Reasoning API...")
    backend_proc = subprocess.Popen(
        ["python", "backend/run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 4. Create Public Tunnel (Wait for boot)
    time.sleep(5)
    print("🔗 Creating Public Dashboard Tunnel...")
    print("--- ACCESS LINK BELOW ---")
    subprocess.run(["npx", "localtunnel", "--port", "8000"], check=False)

if __name__ == "__main__":
    setup_kaggle()
