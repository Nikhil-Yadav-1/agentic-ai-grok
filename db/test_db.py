import os
import sys
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Conversation
from backend.config import DATABASE_URL

def test_database():
    """Test database connection and operations"""
    print("Testing database connection...")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    db = SessionLocal()
    
    try:
        # Add a test conversation
        print("Adding test conversation...")
        test_conversation = Conversation(
            user_message="Hello, this is a test message",
            bot_response="This is a test response from the bot"
        )
        db.add(test_conversation)
        db.commit()
        db.refresh(test_conversation)
        
        print(f"Added conversation with ID: {test_conversation.id}")
        
        # Query the conversation
        print("Querying conversations...")
        conversations = db.query(Conversation).all()
        
        print(f"Found {len(conversations)} conversations:")
        for conv in conversations:
            print(f"ID: {conv.id}")
            print(f"User: {conv.user_message}")
            print(f"Bot: {conv.bot_response}")
            print(f"Timestamp: {conv.timestamp}")
            print("-" * 30)
        
        print("Database test completed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
