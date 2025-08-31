from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gpt4all import GPT4All
from pathlib import Path
import os
import asyncio
import json

app = FastAPI()

class Ask(BaseModel):
    question: str

model_dir = os.path.join(Path(__file__).parent.resolve(), "models")
model = GPT4All(
    model_name="mistral-7b-instruct-v0.1.Q4_0.gguf",
    model_path=model_dir,
    allow_download=False,
)

@app.get("/")
def health():
    return {"status": "ok"}

async def generate_tokens_json(prompt: str):
    full_response = model.generate(prompt, max_tokens=512)
    chunk_size = 8  # i made smaller chunks for more frequent streaming

    for i in range(0, len(full_response), chunk_size):
        chunk = full_response[i:i + chunk_size]
        
        yield json.dumps({"token": chunk}) + "\n"
        await asyncio.sleep(0.01)  # small delay to simulate streaming

    # this is the Signal completion
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
