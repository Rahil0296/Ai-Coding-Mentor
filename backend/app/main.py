import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from gpt4all import GPT4All
import app.state as state  # Import the shared global state module

logging.basicConfig(level=logging.INFO)

model_dir = os.path.join(Path(__file__).parent.resolve(), "models")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_instance = GPT4All(
            model_name="mistral-7b-instruct-v0.1.Q4_0.gguf",
            model_path=model_dir,
            allow_download=False,
        )
        state.model = model_instance
        state.model_loaded = True
        logging.info("Mistral 7B model loaded successfully.")
    except Exception as e:
        logging.error(f"Model failed to load: {e}")
        state.model = None
        state.model_loaded = False

    yield

    state.model = None
    state.model_loaded = False
    logging.info("Model cleaned up on shutdown.")

app = FastAPI(title="AI Coding Mentor API", lifespan=lifespan)

# Import routers after app and state setup
from app.routes import users, roadmaps, ask, health

app.include_router(users.router)
app.include_router(roadmaps.router)
app.include_router(ask.router)
app.include_router(health.router)
