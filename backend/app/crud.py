from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app.models import User, UserProfile, ConversationHistory, Roadmap
from app.schemas import OnboardRequest, RoadmapCreate


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user_with_profile(db: Session, data: OnboardRequest):
    try:
        new_user = User(
            name=data.name,
            email=data.email,
        )
        
        db.add(new_user)
        db.flush()
        
        new_profile = UserProfile(
            user_id=new_user.id,
            programming_language=data.programming_language,
            learning_style=data.learning_style,
            daily_hours=data.daily_hours,
            goal=data.goal,
            experience=data.experience,
            teaching_mode=data.teaching_mode,  # NEW: Pass teaching_mode from request
            # created_at will use default from model (no need to specify here)
        )
        
        db.add(new_profile)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_profile)
        
        return new_user, new_profile
        
    except SQLAlchemyError as e:
        db.rollback()
        raise e


def create_roadmap(db: Session, roadmap_in: RoadmapCreate):
    roadmap = Roadmap(
        user_id=roadmap_in.user_id,
        roadmap_json=roadmap_in.roadmap_json
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap


def get_roadmaps(db: Session, user_id: int):
    return db.query(Roadmap).filter(
        Roadmap.user_id == user_id
    ).order_by(
        Roadmap.updated_at.desc()
    ).all()


def save_conversation_message(db: Session, user_id: int, message: str, sender: str):
    conv = ConversationHistory(
        user_id=user_id,
        message=message,
        sender=sender
    )
    db.add(conv)
    db.commit()
    return conv
