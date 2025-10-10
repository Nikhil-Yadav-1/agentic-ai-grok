# Chatbot Application

A conversational chatbot application built with LangChain, LangGraph, FastAPI, and a web frontend with database integration for conversation history.

## Project Overview

This project implements a chatbot application with the following components:

- **Backend**: FastAPI server with LangChain and LangGraph for AI conversation
- **Frontend**: Simple and modern chat UI built with HTML, CSS, and JavaScript
- **Database**: SQLite (default) or PostgreSQL for storing conversation history

## Project Structure

```
chatbot-app/
├── backend/                 # Backend server code
│   ├── __init__.py          # Package initialization
│   ├── agent.py             # LangChain + LangGraph agent implementation
│   ├── config.py            # Configuration settings
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Backend dependencies
│   └── test_agent.py        # Agent testing script
├── db/                      # Database related code
│   ├── __init__.py          # Package initialization
│   ├── database.py          # Database utility functions
│   ├── models.py            # SQLAlchemy models
│   ├── setup_db.py          # Database setup script
│   └── test_db.py           # Database testing script
├── frontend/                # Frontend code
│   ├── app.js               # JavaScript for the chat interface
│   ├── index.html           # Main HTML page
│   └── styles.css           # CSS styling
├── .env                     # Environment variables (create from .env.example)
├── .env.example             # Example environment variables
├── open_frontend.sh         # Script to start the frontend server
├── setup.sh                 # Setup script
├── start_backend.sh         # Script to start the backend server
└── README.md                # This file
```

## Features

- **Conversational AI**: Powered by LangChain and LangGraph
- **Context-Aware Responses**: Uses conversation history for better responses
- **Modern Chat UI**: Clean and responsive design
- **Persistent Storage**: Saves all conversations to database
- **API Backend**: RESTful API with FastAPI
- **Easy Setup**: Simple scripts to get started quickly

## Setup Instructions

### Quick Setup

1. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   ./setup.sh
   ```

2. Update the `.env` file with your language model API key.

### Manual Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

4. Update the `.env` file with your language model API key.

5. Set up the database:
   ```bash
   python db/setup_db.py
   ```

## Running the Application

### Start the Backend Server

```bash
./start_backend.sh
```

Or manually:

```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend Server

```bash
./open_frontend.sh
```

Or manually:

```bash
cd frontend
python -m http.server 8080
```

Then open your browser and navigate to: http://localhost:8080

## API Endpoints

- `GET /`: Welcome message
- `GET /conversations`: Get recent conversations
- `POST /chat`: Send a message to the chatbot

## Database Configuration

By default, the application uses SQLite. To use PostgreSQL:

1. Update the `DATABASE_URL` in your `.env` file:
   ```
   DATABASE_URL=postgresql://username:password@localhost/chatbot_db
   ```

2. Make sure you have PostgreSQL installed and running.

## Testing

### Test the Agent

```bash
python backend/test_agent.py
```

### Test the Database

```bash
python db/test_db.py
```

## Future Enhancements

- Multiple specialized agents with routing logic
- User authentication and personalized conversations
- Redis for chat history caching
- Real-time response streaming
- Docker deployment with Gunicorn/Uvicorn
- Voice input/output capabilities
- Integration with external knowledge bases
