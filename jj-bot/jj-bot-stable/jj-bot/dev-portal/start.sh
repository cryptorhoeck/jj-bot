#!/bin/bash

# JJ-Bot Developer Portal Startup Script

cd ~/jj-bot/dev-portal

# Check if virtual environment exists, create if not
if [ ! -d "../.venv" ]; then
    echo "Virtual environment not found. Please run from main JJ-Bot directory first."
    exit 1
fi

# Activate virtual environment
source ../.venv/bin/activate

# Install dev portal dependencies
pip install jinja2 psutil

# Start the developer portal
echo "Starting JJ-Bot Developer Portal on http://127.0.0.1:8001"
python app.py
