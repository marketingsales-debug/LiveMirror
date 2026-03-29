#!/bin/bash
# ============================================
# LiveMirror Staging Deployment Script
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 LiveMirror Staging Deployment"
echo "================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || COMPOSE_CMD="docker compose" || COMPOSE_CMD="docker-compose"

cd "$PROJECT_ROOT"

# Check for staging env file
if [ ! -f ".env.staging" ]; then
    echo "⚠️  .env.staging not found. Creating from example..."
    cp .env.staging.example .env.staging
    echo "📝 Please edit .env.staging with your actual values"
    exit 1
fi

# Build frontend if needed
if [ ! -d "frontend/dist" ]; then
    echo "📦 Building frontend..."
    cd frontend
    npm ci
    npm run build
    cd ..
fi

# Pull latest images
echo "📥 Pulling latest images..."
$COMPOSE_CMD -f docker-compose.staging.yml pull

# Build application
echo "🔨 Building application..."
$COMPOSE_CMD -f docker-compose.staging.yml build

# Stop existing containers
echo "🛑 Stopping existing containers..."
$COMPOSE_CMD -f docker-compose.staging.yml down --remove-orphans || true

# Start services
echo "▶️  Starting services..."
$COMPOSE_CMD -f docker-compose.staging.yml up -d

# Wait for health check
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
if curl -s http://localhost:5001/health | grep -q "ok"; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    $COMPOSE_CMD -f docker-compose.staging.yml logs api
    exit 1
fi

if curl -s http://localhost:3000/health | grep -q "OK"; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️  Frontend health check failed (may be normal if no build)"
fi

echo ""
echo "🎉 Deployment complete!"
echo "   API:      http://localhost:5001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "📊 View logs: docker-compose -f docker-compose.staging.yml logs -f"
