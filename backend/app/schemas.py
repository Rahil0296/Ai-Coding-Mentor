from pydantic import BaseModel, Field
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
    language: str
    learning_style: str
    daily_hours: int
    goal: str
    experience: str

class RoadmapCreate(BaseModel):
    user_id: int
    roadmap_json: Any

class RoadmapOut(BaseModel):
    id: int
    user_id: int
    roadmap_json: Any
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
