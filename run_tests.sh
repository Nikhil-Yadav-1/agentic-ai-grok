#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Run database tests
echo "Running database tests..."
python db/test_db.py

echo ""
echo "----------------------------------------"
echo ""

# Run agent tests
echo "Running agent tests..."
python backend/test_agent.py
