import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List

from backend.config import DATABASE_URL
from db.models import Conversation

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_recent_conversations(db, limit: int = 5) -> List[Conversation]:
    """Get the most recent conversations from the database"""
    return db.query(Conversation).order_by(Conversation.timestamp.desc()).limit(limit).all()

def save_conversation(db, user_message: str, bot_response: str) -> Conversation:
    """Save a new conversation to the database"""
    conversation = Conversation(user_message=user_message, bot_response=bot_response)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation
