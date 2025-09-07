from sqlalchemy.orm import Session
from app.models import UserProfile, ConversationHistory, Roadmap
from app.schemas import OnboardRequest, RoadmapCreate

def get_user(db: Session, user_id: int):
    return db.query(UserProfile).filter(UserProfile.id == user_id).first()

def create_user(db: Session, data: OnboardRequest):
    user = UserProfile(
        language=data.language,
        learning_style=data.learning_style,
        daily_hours=data.daily_hours,
        goal=data.goal,
        experience=data.experience,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_roadmap(db: Session, roadmap_in: RoadmapCreate):
    roadmap = Roadmap(user_id=roadmap_in.user_id, roadmap_json=roadmap_in.roadmap_json)
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap

def get_roadmaps(db: Session, user_id: int):
    return db.query(Roadmap).filter(Roadmap.user_id == user_id).order_by(Roadmap.updated_at.desc()).all()

def save_conversation_message(db: Session, user_id: int, message: str, sender: str):
    conv = ConversationHistory(user_id=user_id, message=message, sender=sender)
    db.add(conv)
    db.commit()
    return conv
