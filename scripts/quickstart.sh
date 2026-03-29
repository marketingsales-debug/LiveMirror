#!/bin/bash
# ============================================
# LiveMirror Quick Start Script
# For local development and testing
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 LiveMirror Quick Start"
echo "========================="

cd "$PROJECT_ROOT"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q torch transformers sentence-transformers numpy pytest pytest-asyncio

# Install backend
cd backend
pip install -q -e ".[dev]"
cd ..

# Check for .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Creating from example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API keys"
fi

# Run tests
echo ""
echo "🧪 Running tests..."
python -m pytest tests/ -v --tb=short --ignore=tests/unit/learning/test_loop.py -q

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the API server:"
echo "  cd backend && uv run python run.py"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
