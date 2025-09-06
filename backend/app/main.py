import os
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Any
import traceback
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from app.models import UserProfile, ConversationHistory, Roadmap

from gpt4all import GPT4All


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

# These are the Pydantic Models : 


class HistoryTurn(BaseModel):
    user: str
    assistant: str


class Ask(BaseModel):
    user_id: int
    question: str = Field(..., min_length=5, max_length=1000, description="Your programming question.")
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


from datetime import datetime

class RoadmapOut(BaseModel):
    id: int
    user_id: int
    roadmap_json: Any
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }





# This Loads the AI model once at startup :


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



# These are the Helper Functions : 


def build_prompt_with_roadmap(user_id: int, question: str, history: Optional[List[HistoryTurn]], db: Session) -> str:
    prompt = ""

    if history:
        for turn in history:
            prompt += f"User: {turn.user}\nAssistant: {turn.assistant}\n"

    latest_roadmap = db.query(Roadmap).filter(Roadmap.user_id == user_id).order_by(Roadmap.updated_at.desc()).first()
    if latest_roadmap:
        prompt += f"\nUser's current learning roadmap:\n{json.dumps(latest_roadmap.roadmap_json, indent=2)}\n\n"

    prompt += f"User: {question}\nAssistant:"
    return prompt


async def generate_tokens_json(prompt: str):
    if not model_loaded or model is None:
        yield json.dumps({"error": "Model not loaded."}) + "\n"
        return

    try:
        full_response = model.generate(prompt, max_tokens=512)
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"
        logging.error(f"Model inference error: {e}")
        return

    chunk_size = 8
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i : i + chunk_size]
        yield json.dumps({"token": chunk}) + "\n"
        await asyncio.sleep(0.01)

    final_payload = {
        "question": prompt,
        "prompt": prompt,
        "answer": full_response,
        "tokens_streamed": len(full_response),
        "model": "mistral-7b-instruct-v0.1",
    }
    yield json.dumps(final_payload) + "\n"
    yield json.dumps({"done": True}) + "\n"



# These are the API Endpoints i created :


@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": model_loaded}


@app.post("/onboard")
def onboard(data: OnboardRequest, db: Session = Depends(get_db)):
    user_profile = UserProfile(
        language=data.language,
        learning_style=data.learning_style,
        daily_hours=data.daily_hours,
        goal=data.goal,
        experience=data.experience,
    )
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)
    return {"message": "User profile created", "user_id": user_profile.id}


@app.post("/ask")
async def ask(body: Ask, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    question = body.question.strip()
    if not question or len(question) < 5 or len(question) > 1000:
        raise HTTPException(status_code=400, detail="Invalid question length.")

    prompt = build_prompt_with_roadmap(body.user_id, question, body.history, db)

    async def generate_and_store():
        # Save user's question
        user_msg = ConversationHistory(user_id=body.user_id, message=question, sender="user")
        db.add(user_msg)
        db.commit()

        full_answer = ""
        async for chunk in generate_tokens_json(prompt):
            data = json.loads(chunk)
            if "token" in data:
                full_answer += data["token"]
            yield chunk

        # Save assistant's answer after streaming completes
        assistant_msg = ConversationHistory(user_id=body.user_id, message=full_answer, sender="assistant")
        db.add(assistant_msg)
        db.commit()

    return StreamingResponse(generate_and_store(), media_type="application/json")


@app.get("/history/{user_id}")
def get_conversation_history(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    history = (
        db.query(ConversationHistory)
        .filter(ConversationHistory.user_id == user_id)
        .order_by(ConversationHistory.timestamp.asc())
        .all()
    )

    return [
        {"sender": entry.sender, "message": entry.message, "timestamp": entry.timestamp.isoformat()}
        for entry in history
    ]


import traceback

@app.post("/roadmaps", response_model=RoadmapOut)
def create_roadmap(roadmap_in: RoadmapCreate, db: Session = Depends(get_db)):
    try:
        user = db.query(UserProfile).filter(UserProfile.id == roadmap_in.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        roadmap = Roadmap(user_id=roadmap_in.user_id, roadmap_json=roadmap_in.roadmap_json)
        db.add(roadmap)
        db.commit()
        db.refresh(roadmap)
        return roadmap

    except Exception as e:
        traceback_str = traceback.format_exc()
        logging.error(f"Roadmap creation failed: {traceback_str}")
        raise HTTPException(status_code=500, detail="Internal server error")



@app.get("/roadmaps/{user_id}", response_model=List[RoadmapOut])
def get_roadmaps(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    roadmaps = db.query(Roadmap).filter(Roadmap.user_id == user_id).order_by(Roadmap.updated_at.desc()).all()
    return roadmaps


@app.put("/roadmaps/{roadmap_id}", response_model=RoadmapOut)
def update_roadmap(roadmap_id: int, roadmap_in: RoadmapCreate = Body(...), db: Session = Depends(get_db)):
    roadmap = db.query(Roadmap).filter(Roadmap.id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    roadmap.roadmap_json = roadmap_in.roadmap_json
    db.commit()
    db.refresh(roadmap)
    return roadmap
