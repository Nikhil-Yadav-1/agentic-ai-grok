from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import ChatbotAgent
from backend.config import DATABASE_URL
from db.database import get_db, get_recent_conversations, save_conversation
from db.models import Conversation

# Initialize FastAPI app
app = FastAPI(title="Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot agent
chatbot_agent = ChatbotAgent()

# Define request and response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    conversation_id: int

class ConversationResponse(BaseModel):
    id: int
    user_message: str
    bot_response: str
    timestamp: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Chatbot API"}

@app.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent conversations"""
    conversations = get_recent_conversations(db, limit)
    return [conversation.to_dict() for conversation in conversations]

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Process a chat message and return a response"""
    try:
        # Initialize chat history
        chat_history = []
        
        try:
            # Try to get recent conversations for context
            recent_conversations = get_recent_conversations(db)
            
            # Format conversations for the agent
            for conv in recent_conversations:
                chat_history.append({"role": "user", "content": conv.user_message})
                chat_history.append({"role": "assistant", "content": conv.bot_response})
        except Exception as db_error:
            # If there's an error getting conversations, just continue with empty history
            print(f"Warning: Could not retrieve conversation history: {str(db_error)}")
            # Ensure the database tables exist
            import sqlite3
            conn = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            conn.commit()
            conn.close()
        
        # Process the message
        response = chatbot_agent.process_message(request.message, chat_history)
        
        try:
            # Try to save the conversation
            conversation = save_conversation(db, request.message, response)
            conversation_id = conversation.id
        except Exception as save_error:
            print(f"Warning: Could not save conversation: {str(save_error)}")
            conversation_id = 0
        
        return {
            "response": response,
            "conversation_id": conversation_id
        }
    except Exception as e:
        import traceback
        print(f"Error in /chat endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    from backend.config import API_HOST, API_PORT
    
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
