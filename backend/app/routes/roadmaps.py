from fastapi import APIRouter, Depends, HTTPException
from typing import List
import json
from sqlalchemy.orm import Session
from app.schemas import RoadmapCreate, RoadmapOut
from app.crud import get_user, get_roadmaps
from app.dependencies import get_db
from app.models import Roadmap

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

@router.post("", response_model=RoadmapOut)
def create_roadmap_route(roadmap_in: RoadmapCreate, db: Session = Depends(get_db)):
    user = get_user(db, roadmap_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert dict to JSON string if needed
    roadmap_json = roadmap_in.roadmap_json
    if isinstance(roadmap_json, dict):
        roadmap_json = json.dumps(roadmap_json)
    
    # Create roadmap
    roadmap = Roadmap(
        user_id=roadmap_in.user_id,
        roadmap_json=roadmap_json
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    
    return roadmap

@router.get("/{user_id}", response_model=List[RoadmapOut])
def get_roadmaps_route(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return get_roadmaps(db, user_id)