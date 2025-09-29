from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.code_executor import CodeExecutor
from app.dependencies import get_db
from app.crud import get_user

router = APIRouter(prefix="/execute", tags=["execute"])

# Initialize code executor
executor = CodeExecutor(timeout=5)


class ExecuteRequest(BaseModel):
    user_id: int
    code: str
    language: str = "python"


@router.post("")
async def execute_code(request: ExecuteRequest, db: Session = Depends(get_db)):
    """
    Execute code snippets safely and return results.
    """
    # Verify user exists
    user = get_user(db, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Execute code
    result = await executor.execute(request.code, request.language)
    
    return result