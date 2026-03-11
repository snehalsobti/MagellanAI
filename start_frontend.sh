#!/bin/bash

# Start Frontend for MagellanAI

echo "=========================================="
echo "Starting MagellanAI Frontend"
echo "=========================================="

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example"
    cp .env.example .env
fi

echo ""
echo "Starting Svelte development server..."
echo "The app will open at http://localhost:5173"
echo "Press Ctrl+C to stop"
echo ""

npm run dev

