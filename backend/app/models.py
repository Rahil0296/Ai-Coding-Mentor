from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    profile = relationship(
        "UserProfile",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    language = Column(String, nullable=False)
    learning_style = Column(String, nullable=False)
    daily_hours = Column(Integer, nullable=False)
    goal = Column(String, nullable=False)
    experience = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="profile")
    roadmaps = relationship("Roadmap", back_populates="user")
    conversations = relationship("ConversationHistory", back_populates="user")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    roadmap_json = Column(Text, nullable=False)  # Adjust type if needed (JSONB for PostgreSQL)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("UserProfile", back_populates="roadmaps")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # Values: "user" or "assistant"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserProfile", back_populates="conversations")
