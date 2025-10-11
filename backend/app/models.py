from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

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
    
    conversations = relationship("ConversationHistory", back_populates="user")
    roadmaps = relationship("Roadmap", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    programming_language = Column(String, nullable=False)
    learning_style = Column(String, nullable=False)
    daily_hours = Column(Integer, nullable=False)
    goal = Column(String, nullable=False)
    experience = Column(String, nullable=False)
    
    # NEW: Adaptive teaching mode fields
    teaching_mode = Column(String, default="guided", nullable=False)
    min_confidence_threshold = Column(Integer, default=70, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    roadmap_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="roadmaps")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String, nullable=False)  # Values: "user" or "assistant"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="conversations")


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False)  # Groups traces by session
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ReAct cycle data
    user_input = Column(Text, nullable=False)
    reasoning = Column(Text)  # What the agent thought
    action_taken = Column(String)  # Which tool/action was selected
    action_parameters = Column(Text)  # JSON string of parameters
    observation = Column(Text)  # What happened
    reflection = Column(Text)  # Agent's self-evaluation

    # Performance metrics
    success = Column(Boolean, default=False)
    confidence_score = Column(Integer)  # 0-100
    execution_time_ms = Column(Integer)
    error_message = Column(Text)

    # Learning data
    pattern_detected = Column(String)  # e.g., "user_confusion", "wrong_tool_selected"
    improvement_suggestion = Column(Text)  # What to do differently next time

    user = relationship("User")


class AgentPerformanceMetrics(Base):
    __tablename__ = "agent_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Aggregate metrics
    total_interactions = Column(Integer, default=0)
    successful_interactions = Column(Integer, default=0)
    average_confidence = Column(Integer, default=0)
    average_execution_time_ms = Column(Integer, default=0)

    # Tool usage stats (JSON)
    tool_usage_stats = Column(Text)  # {"explain": 45, "exercise": 30, ...}
    common_failures = Column(Text)  # {"wrong_difficulty": 15, ...}

    user = relationship("User")
