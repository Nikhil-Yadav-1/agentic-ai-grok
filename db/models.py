from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_message": self.user_message,
            "bot_response": self.bot_response,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
