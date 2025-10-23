from fastapi import APIRouter
import app.state as state

router = APIRouter()

@router.get("/health", tags=["health"])
def health_check():
    # return a stable shape the tests expect
    return {"status": "healthy", "model_loaded": getattr(state, "model_loaded", False)}
