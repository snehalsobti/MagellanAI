#!/bin/bash

# Start Backend API Server for MagellanAI

echo "=========================================="
echo "Starting MagellanAI Backend API Server"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your OPENAI_API_KEY"
    echo ""
    echo "Example:"
    echo "  echo 'OPENAI_API_KEY=your_key_here' > .env"
    echo ""
    exit 1
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

