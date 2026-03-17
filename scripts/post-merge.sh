#!/bin/bash
set -e

echo "=== Post-merge setup ==="

echo "Installing Python dependencies..."
pip install -r requirements.txt -q

echo "Post-merge setup complete."
