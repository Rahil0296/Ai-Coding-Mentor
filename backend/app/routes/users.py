from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import OnboardRequest
from app.crud import create_user
from app.dependencies import get_db
 
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/onboard")
def onboard(data: OnboardRequest, db: Session = Depends(get_db)):
    user = create_user(db, data)
    return {"message": "User profile created", "user_id": user.id}
