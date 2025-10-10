#!/bin/bash

echo "Chatbot Application Demo"
echo "========================"
echo ""
echo "This script will demonstrate the full application flow."
echo ""

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Setting up the virtual environment and dependencies..."
    ./setup.sh
    echo ""
fi

# Activate the virtual environment
source venv/bin/activate

# Set up the database
echo "Setting up the database..."
python db/setup_db.py
echo ""

# Run the database test
echo "Testing the database..."
python db/test_db.py
echo ""

echo "The application is now ready to run!"
echo ""
echo "To start the backend server, open a new terminal and run:"
echo "  cd $(pwd) && ./start_backend.sh"
echo ""
echo "To start the frontend server, open another terminal and run:"
echo "  cd $(pwd) && ./open_frontend.sh"
echo ""
echo "Then open your browser and navigate to: http://localhost:8080"
echo ""
echo "Enjoy your chatbot application!"
