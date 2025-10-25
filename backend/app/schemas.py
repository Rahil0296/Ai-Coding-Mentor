from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any
from datetime import datetime


class HistoryTurn(BaseModel):
    user: str
    assistant: str


class Ask(BaseModel):
    user_id: int
    question: str = Field(..., min_length=5, max_length=1000)
    history: Optional[List[HistoryTurn]] = None


class OnboardRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    programming_language: str
    learning_style: str
    daily_hours: int
    goal: str
    experience: str
    teaching_mode: Optional[str] = "guided"  # NEW


class RoadmapCreate(BaseModel):
    user_id: int
    roadmap_json: Any


class RoadmapOut(BaseModel):
    id: int
    user_id: int
    roadmap_json: Any
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    programming_language: str
    learning_style: str
    daily_hours: int
    goal: str
    experience: str
    created_at: datetime
    teaching_mode: str  # NEW
    min_confidence_threshold: int  # NEW

    class Config:
        from_attributes = True


class UserOnboardResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    profile: UserProfileResponse

    class Config:
        from_attributes = True