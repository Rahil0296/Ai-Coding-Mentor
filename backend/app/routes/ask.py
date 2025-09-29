import json
import logging
import asyncio
from typing import AsyncGenerator

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas import Ask
from app.crud import get_user, save_conversation_message, get_roadmaps
from app.dependencies import get_db
from app.agent_engine import AgentEngine
import app.state as state

router = APIRouter(prefix="/ask", tags=["ask"])

# Initialize agent engine
agent_engine = AgentEngine()


def get_user_profile_dict(db: Session, user_id: int) -> dict:
    """Get user profile as dictionary for agent engine."""
    user = get_user(db, user_id)
    if user and user.profile:
        return {
            "learning_style": user.profile.learning_style,
            "experience": user.profile.experience,
            "daily_hours": user.profile.daily_hours,
            "goal": user.profile.goal,
            "language": user.profile.language
        }
    return {}


async def stream_ollama_chat(prompt: str) -> AsyncGenerator[dict, None]:
    """Stream responses from Ollama."""
    base_url = getattr(state, "ollama_base_url", "http://localhost:11434")
    model_name = getattr(state, "model_name", None)
    loaded = getattr(state, "model_loaded", False)
    
    if not loaded or not model_name:
        yield {"error": "Model not loaded."}
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

                if "message" in obj and "content" in obj["message"]:
                    yield {"token": obj["message"]["content"]}

                if obj.get("done"):
                    yield {"done": True}
                    break
    except Exception as e:
        yield {"error": str(e)}


@router.post("")
async def ask_route(body: Ask, db: Session = Depends(get_db)):
    user = get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    question = body.question.strip()
    if len(question) < 5 or len(question) > 1000:
        raise HTTPException(status_code=400, detail="Invalid question length.")

    # Get user profile and roadmap
    user_profile = get_user_profile_dict(db, body.user_id)
    latest_roadmaps = get_roadmaps(db, body.user_id)
    latest_roadmap = latest_roadmaps[0].roadmap_json if latest_roadmaps else None

    # Create agent-enhanced prompt
    agent_prompt = agent_engine.create_agent_prompt(
        user_question=question,
        user_profile=user_profile,
        roadmap=latest_roadmap
    )

    # Add conversation history if provided
    if body.history:
        history_text = "\n\nPrevious conversation:\n"
        for turn in body.history:
            history_text += f"User: {turn.user}\nAssistant: {turn.assistant}\n"
        agent_prompt = history_text + "\n" + agent_prompt

    async def generate_and_store():
        # Save user message
        save_conversation_message(db, body.user_id, question, "user")

        full_answer = ""
        errored = False

        # Stream through agent engine for structured responses
        ollama_stream = stream_ollama_chat(agent_prompt)
        
        async for agent_chunk in agent_engine.process_streaming_response(ollama_stream):
            # Convert agent actions to JSON for streaming
            yield json.dumps(agent_chunk) + "\n"
            
            # Accumulate full answer for storage
            if agent_chunk.get("type") == "agent_action" and "content" in agent_chunk:
                if agent_chunk["action"] == "think":
                    # Include thinking in stored answer but marked
                    full_answer += f"[Thinking: {agent_chunk['content']}]\n"
                else:
                    full_answer += agent_chunk['content'] + "\n"
            
            if agent_chunk.get("type") == "error":
                errored = True

        # Save assistant reply if successful
        if not errored and full_answer.strip():
            save_conversation_message(db, body.user_id, full_answer, "assistant")

    return StreamingResponse(generate_and_store(), media_type="application/json")


@router.post("/simple")
async def simple_ask_route(body: Ask, db: Session = Depends(get_db)):
    """
    Original simple ask endpoint without agent capabilities.
    Kept for backward compatibility or when agent mode is not needed.
    """
    user = get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build simple prompt with roadmap context
    prompt = ""
    if body.history:
        for turn in body.history:
            prompt += f"User: {turn.user}\nAssistant: {turn.assistant}\n"

    latest_roadmaps = get_roadmaps(db, body.user_id)
    if latest_roadmaps:
        latest_roadmap = latest_roadmaps[0]
        prompt += (
            "\nUser's current learning roadmap:\n"
            f"{json.dumps(latest_roadmap.roadmap_json, indent=2)}\n\n"
        )

    prompt += f"User: {body.question}\nAssistant:"

    async def generate_simple():
        save_conversation_message(db, body.user_id, body.question, "user")
        full_answer = ""

        async for chunk in stream_ollama_chat(prompt):
            if "token" in chunk:
                full_answer += chunk["token"]
                yield json.dumps({"token": chunk["token"]}) + "\n"
            elif "done" in chunk:
                yield json.dumps({"done": True}) + "\n"
            elif "error" in chunk:
                yield json.dumps({"error": chunk["error"]}) + "\n"
                return

        if full_answer.strip():
            save_conversation_message(db, body.user_id, full_answer, "assistant")

    return StreamingResponse(generate_simple(), media_type="application/json")