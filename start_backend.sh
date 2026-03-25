#!/bin/bash

# Start Backend API Server for MagellanAI

echo "=========================================="
echo "Starting MagellanAI Backend API Server"
echo "=========================================="

# Load .env file if present, but don't require it
# (env vars can also be set in the shell environment or on the hosting platform)
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    set -a
    source .env
    set +a
fi

# Warn if critical env vars are missing but still attempt to start
if [ -z "$OPENAI_API_KEY" ]; then
    echo "WARNING: OPENAI_API_KEY is not set."
    echo "Set it in a .env file, export it in your shell, or configure it on your hosting platform."
    echo ""
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Check if Python dependencies are installed
echo "Installing Python dependencies..."
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements_api.txt

echo ""
echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

.venv/bin/python api_server.py

