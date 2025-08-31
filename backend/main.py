# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gpt4all import GPT4All
from pathlib import Path
import os
import asyncio
import json

app = FastAPI(title="AI Coding Mentor API")

# Request body model
class Ask(BaseModel):
    question: str

# Load model
model_dir = os.path.join(Path(__file__).parent.resolve(), "models")
model = GPT4All(
    model_name="mistral-7b-instruct-v0.1.Q4_0.gguf",
    model_path=model_dir,
    allow_download=False,
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": bool(model)}

async def generate_tokens_json(prompt: str):
    """
    Stream tokens in small JSON chunks, then yield a final response object.
    """
    try:
        full_response = model.generate(prompt, max_tokens=512)
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"
        return

    chunk_size = 8  # Smaller chunks for more frequent streaming

    # Stream individual token chunks
    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i:i + chunk_size]
        yield json.dumps({"token": chunk}) + "\n"
        await asyncio.sleep(0.01)

    # Send final complete response
    final_payload = {
        "question": prompt,
        "answer": full_response,
        "tokens_streamed": len(full_response),
        "model": "mistral-7b-instruct-v0.1"
    }
    yield json.dumps(final_payload) + "\n"
    yield json.dumps({"done": True}) + "\n"

@app.post("/ask")
async def ask(body: Ask):
    try:
        return StreamingResponse(
            generate_tokens_json(body.question),
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
