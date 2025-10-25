"""
Analytics Schemas
Pydantic models for analytics endpoints with strict validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime


class DailyActivity(BaseModel):
    """Daily activity summary."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    question_count: int = Field(..., ge=0, description="Number of questions asked")
    avg_confidence: int = Field(..., ge=0, le=100, description="Average confidence score")
    
    @validator('date')
    def validate_date_format(cls, v):
        """Ensure date is in correct format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class TopicFrequency(BaseModel):
    """Frequency of questions by topic."""
    topic: str = Field(..., min_length=1, max_length=100)
    count: int = Field(..., ge=0)


class TeachingModeStats(BaseModel):
    """Statistics per teaching mode."""
    guided: int = Field(..., ge=0)
    debug_practice: int = Field(..., ge=0)
    perfect: int = Field(..., ge=0)


class StreakInfo(BaseModel):
    """User's learning streak information."""
    current_streak_days: int = Field(..., ge=0)
    longest_streak_days: int = Field(..., ge=0)
    last_activity_date: Optional[str] = None
    
    @validator('last_activity_date')
    def validate_last_activity_date(cls, v):
        """Validate date format if provided."""
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v


class PerformanceMetrics(BaseModel):
    """Overall performance metrics."""
    total_questions: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0.0, le=100.0)
    avg_confidence: int = Field(..., ge=0, le=100)
    avg_response_time_ms: int = Field(..., ge=0)


class AnalyticsResponse(BaseModel):
    """
    Complete analytics response.
    
    Security considerations:
    - All integer fields validated with ge=0
    - Percentages capped at 0-100
    - Dates validated for format
    - String fields have max length limits
    """
    user_id: int = Field(..., gt=0)
    
    # Overview metrics
    total_questions: int = Field(..., ge=0)
    questions_this_week: int = Field(..., ge=0)
    questions_today: int = Field(..., ge=0)
    
    # Performance
    success_rate: float = Field(..., ge=0.0, le=100.0, description="Success rate percentage")
    avg_confidence_score: int = Field(..., ge=0, le=100)
    avg_response_time_ms: int = Field(..., ge=0)
    
    # Trends (last 7 days)
    daily_activity: List[DailyActivity] = Field(..., max_items=30, description="Max 30 days")
    confidence_trend: List[int] = Field(..., max_items=30, description="Confidence scores over time")
    
    # Learning patterns
    top_topics: List[TopicFrequency] = Field(..., max_items=10, description="Top 10 topics")
    teaching_mode_usage: TeachingModeStats
    
    # Engagement
    streak: StreakInfo
    total_learning_time_hours: float = Field(..., ge=0.0)
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "total_questions": 45,
                "questions_this_week": 12,
                "questions_today": 3,
                "success_rate": 87.5,
                "avg_confidence_score": 78,
                "avg_response_time_ms": 15420,
                "daily_activity": [
                    {"date": "2025-10-23", "question_count": 5, "avg_confidence": 80}
                ],
                "confidence_trend": [65, 70, 72, 75, 78, 80, 82],
                "top_topics": [
                    {"topic": "loops", "count": 15},
                    {"topic": "functions", "count": 12}
                ],
                "teaching_mode_usage": {
                    "guided": 30,
                    "debug_practice": 10,
                    "perfect": 5
                },
                "streak": {
                    "current_streak_days": 7,
                    "longest_streak_days": 14,
                    "last_activity_date": "2025-10-23"
                },
                "total_learning_time_hours": 12.5,
                "generated_at": "2025-10-23T05:45:00Z"
            }
        }


class AnalyticsError(BaseModel):
    """Standard error response for analytics endpoints."""
    error: str
    detail: str
    user_id: Optional[int] = None