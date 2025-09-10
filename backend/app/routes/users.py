from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import OnboardRequest, UserOnboardResponse, UserProfileResponse
from app.crud import create_user_with_profile
from app.dependencies import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/onboard", response_model=UserOnboardResponse)
def onboard_user(data: OnboardRequest, db: Session = Depends(get_db)):
    try:
        user, profile = create_user_with_profile(db, data)

        profile_response = UserProfileResponse(**profile.__dict__)

        response = UserOnboardResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            profile=profile_response
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed onboarding: {str(e)}")

