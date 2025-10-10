#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Start the FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
