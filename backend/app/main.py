from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from gpt4all import GPT4All
from pathlib import Path
import os
import asyncio
import json
import logging
from typing import List, Optional
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from dotenv import load_dotenv

from app.models import UserProfile  # Import your SQLAlchemy model

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="AI Coding Mentor API")
logging.basicConfig(level=logging.INFO)

class HistoryTurn(BaseModel):
    user: str
    assistant: str

class Ask(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000, description="Your programming question.")
    history: Optional[List[HistoryTurn]] = Field(default=None, description="Conversation history.")

# New Pydantic model for onboarding input
class OnboardRequest(BaseModel):
    language: str = Field(..., description="Programming language user wants to learn")
    learning_style: str = Field(..., description="Preferred learning style")
    daily_hours: int = Field(..., gt=0, description="Hours per day user can dedicate")
    goal: str = Field(..., description="User's main goal")
    experience: str = Field(..., description="User's experience level")

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": True}

model_dir = os.path.join(Path(__file__).parent.resolve(), "models")
try:
    model = GPT4All(
        model_name="mistral-7b-instruct-v0.1.Q4_0.gguf",
        model_path=model_dir,
        allow_download=False,
    )
    model_loaded = True
except Exception as e:
    logging.error(f"Model failed to load: {e}")
    model = None
    model_loaded = False

def build_prompt(question: str, history: Optional[List[HistoryTurn]]) -> str:
    prompt = ""
    if history:
        for turn in history:
            prompt += f"User: {turn.user}\nAssistant: {turn.assistant}\n"
    prompt += f"User: {question}\nAssistant:"
    return prompt

async def generate_tokens_json(prompt: str):
    if not model_loaded or model is None:
        yield json.dumps({"error": "Model not loaded."}) + "\n"
        return

    try:
        full_response = model.generate(prompt, max_tokens=512)
    except Exception as e:
        logging.error(f"Model inference error: {e}")
        yield json.dumps({"error": f"Model error: {str(e)}"}) + "\n"
        return

    chunk_size = 8
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i:i + chunk_size]
        yield json.dumps({"token": chunk}) + "\n"
        await asyncio.sleep(0.01)

    final_payload = {
        "prompt": prompt,
        "answer": full_response,
        "tokens_streamed": len(full_response),
        "model": "mistral-7b-instruct-v0.1"
    }
    yield json.dumps(final_payload) + "\n"
    yield json.dumps({"done": True}) + "\n"

@app.post("/ask")
async def ask(body: Ask, request: Request):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) < 5:
        raise HTTPException(status_code=400, detail="Question too short.")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long.")

    logging.info(f"Received question: {question}")
    prompt = build_prompt(question, body.history)

    try:
        return StreamingResponse(
            generate_tokens_json(prompt),
            media_type="application/json"
        )
    except Exception as e:
        logging.error(f"Streaming error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error. Please try again later."}
        )

@app.post("/onboard")
def onboard(data: OnboardRequest, db: Session = Depends(get_db)):
    # Save user onboarding info to the database
    try:
        user_profile = UserProfile(
            language=data.language,
            learning_style=data.learning_style,
            daily_hours=data.daily_hours,
            goal=data.goal,
            experience=data.experience
        )
        db.add(user_profile)
        db.commit()
        db.refresh(user_profile)
        return {"message": "User profile created", "user_id": user_profile.id}
    except Exception as e:
        logging.error(f"DB error during onboarding: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

