import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.schemas import Ask
from app.crud import get_user, save_conversation_message
from app.dependencies import get_db
import app.state as state  # Import the entire state module

router = APIRouter(prefix="/ask", tags=["ask"])

def build_prompt_with_roadmap(user_id: int, question: str, history, db: Session) -> str:
    prompt = ""
    if history:
        for turn in history:
            prompt += f"User: {turn.user}\nAssistant: {turn.assistant}\n"

    from app.crud import get_roadmaps  # Avoid circular import
    latest_roadmaps = get_roadmaps(db, user_id)
    if latest_roadmaps:
        latest_roadmap = latest_roadmaps[0]
        prompt += f"\nUser's current learning roadmap:\n{json.dumps(latest_roadmap.roadmap_json, indent=2)}\n\n"

    prompt += f"User: {question}\nAssistant:" 
    return prompt

async def generate_tokens_json(prompt: str):
    logging.info(f"Model loaded flag: {state.model_loaded}, model object: {state.model}")

    if not state.model_loaded or state.model is None:
        yield json.dumps({"error": "Model not loaded."}) + "\n"
        return

    try:
        full_response = state.model.generate(prompt, max_tokens=512)
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"
        return

    chunk_size = 8
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i: i + chunk_size]
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

@router.post("")
async def ask_route(body: Ask, db: Session = Depends(get_db)):
    user = get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    question = body.question.strip()
    if len(question) < 5 or len(question) > 1000:
        raise HTTPException(status_code=400, detail="Invalid question length.")

    prompt = build_prompt_with_roadmap(body.user_id, question, body.history, db)

    async def generate_and_store():
        save_conversation_message(db, body.user_id, question, "user")

        full_answer = ""
        async for chunk in generate_tokens_json(prompt):
            data = json.loads(chunk)
            if "token" in data:
                full_answer += data["token"]
            yield chunk

        save_conversation_message(db, body.user_id, full_answer, "assistant")

    return StreamingResponse(generate_and_store(), media_type="application/json")
