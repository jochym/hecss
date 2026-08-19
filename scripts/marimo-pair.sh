#!/usr/bin/env bash
# marimo-pair integration script for OpenCode
# Usage: ./marimo-pair.sh <notebook_path>

set -e

NOTEBOOK="${1:-notebooks/11_core.py}"
PORT="${2:-2718}"

echo "Starting marimo for $NOTEBOOK on port $PORT..."

# Start marimo in background
marimo run "$NOTEBOOK" --port "$PORT" --no-token --headless &
MARIMO_PID=$!

# Wait for server to start
sleep 3

# Generate pair programming prompt
echo "Generating pair programming prompt for OpenCode..."
marimo pair prompt --url "http://localhost:$PORT" --file "$NOTEBOOK" --opencode

# Cleanup
echo "Press Ctrl+C to stop marimo server (PID: $MARIMO_PID)"
wait $MARIMO_PID