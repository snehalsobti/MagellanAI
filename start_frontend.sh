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

echo ""
echo "Starting React development server..."
echo "The app will open at http://localhost:3000"
echo "Press Ctrl+C to stop"
echo ""

npm start

