from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from sqlalchemy.orm import Session
from app.schemas import RoadmapCreate, RoadmapOut
from app.crud import get_user, create_roadmap, get_roadmaps
from app.dependencies import get_db

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

@router.post("", response_model=RoadmapOut)
def create_roadmap_route(roadmap_in: RoadmapCreate, db: Session = Depends(get_db)):
    user = get_user(db, roadmap_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roadmap = create_roadmap(db, roadmap_in)
    return roadmap

@router.get("/{user_id}", response_model=List[RoadmapOut])
def get_roadmaps_route(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return get_roadmaps(db, user_id)
