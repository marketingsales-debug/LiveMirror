#!/bin/bash
# ==============================================================================
# LiveMirror v2.0 - Oracle Cloud (OCI) Bootstrap Script
# ==============================================================================

set -e

echo "🚀 Starting LiveMirror OCI Bootstrap..."

# 1. Update and Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# 2. Add current user to docker group
sudo usermod -aG docker $USER

# 3. Configure OCI Firewall (Allow 80, 8000, 5173)
echo "🛡️ Configuring Firewall..."
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 5173/tcp
sudo ufw --force enable

# 4. Create local data directories
mkdir -p data/memory data/evolution

# 5. Build and Launch
echo "🐳 Starting Containers..."
docker-compose up -d --build

echo "✅ LiveMirror is now running!"
echo "Dashboard: http://$(curl -s ifconfig.me)"
echo "API: http://$(curl -s ifconfig.me):8000"
