#!/bin/bash

# Create a virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
pip install -r backend/requirements.txt

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please update the .env file with your API key and database settings."
fi

# Set up the database
echo "Setting up the database..."
python db/setup_db.py

echo "Setup complete! You can now start the backend server with:"
echo "source venv/bin/activate && python backend/main.py"
echo "And open the frontend by opening frontend/index.html in your browser."
