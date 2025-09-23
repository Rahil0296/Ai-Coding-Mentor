import json
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas import Ask
from app.crud import get_user, save_conversation_message
from app.dependencies import get_db
import app.state as state  # shared state (ollama_base_url, model_name, model_loaded)

router = APIRouter(prefix="/ask", tags=["ask"])


def build_prompt_with_roadmap(user_id: int, question: str, history, db: Session) -> str:
    prompt = ""
    if history:
        for turn in history:
            prompt += f"User: {turn.user}\nAssistant: {turn.assistant}\n"

    # Avoid circular import at module load
    from app.crud import get_roadmaps

    latest_roadmaps = get_roadmaps(db, user_id)
    if latest_roadmaps:
        latest_roadmap = latest_roadmaps[0]
        prompt += (
            "\nUser's current learning roadmap:\n"
            f"{json.dumps(latest_roadmap.roadmap_json, indent=2)}\n\n"
        )

    prompt += f"User: {question}\nAssistant:"
    return prompt


async def generate_tokens_json(prompt: str):
    base_url = getattr(state, "ollama_base_url", "http://localhost:11434")
    model_name = getattr(state, "model_name", None)
    loaded = getattr(state, "model_loaded", False)
    logging.info(f"Ollama base={base_url}, model={model_name}, loaded={loaded}")

    if not loaded or not model_name:
        yield json.dumps({"error": "Model not loaded."}) + "\n"
        return

    try:
        with requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
            stream=True,
            timeout=None,
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                obj = json.loads(line)

                # Stream incremental content from Ollama
                if "message" in obj and "content" in obj["message"]:
                    yield json.dumps({"token": obj["message"]["content"]}) + "\n"

                # End of stream
                if obj.get("done"):
                    yield json.dumps({"done": True}) + "\n"
                    break
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"


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
        # Save user message first
        save_conversation_message(db, body.user_id, question, "user")

        full_answer = ""
        errored = False

        async for chunk in generate_tokens_json(prompt):
            data = json.loads(chunk)
            if "token" in data:
                full_answer += data["token"]
            if "error" in data:
                errored = True
            yield chunk

        # Only save assistant reply if generation succeeded
        if not errored and full_answer.strip():
            save_conversation_message(db, body.user_id, full_answer, "assistant")

    return StreamingResponse(generate_and_store(), media_type="application/json")
