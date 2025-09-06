from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    language = Column(String, nullable=False)
    learning_style = Column(String, nullable=False)
    daily_hours = Column(Integer, nullable=False)
    goal = Column(String, nullable=False)
    experience = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    roadmaps = relationship("Roadmap", back_populates="user")
    conversations = relationship("ConversationHistory", back_populates="user")


class Roadmap(Base):
    __tablename__ = "roadmaps"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    roadmap_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("UserProfile", back_populates="roadmaps")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # "user" or "assistant"
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserProfile", back_populates="conversations")
