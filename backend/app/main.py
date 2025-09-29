import os
import logging
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI

import app.state as state  # shared global state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure Ollama connection and target model (env overrides allowed)
    state.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    state.model_name = os.getenv("OLLAMA_MODEL", "qwen25_coder_7b_local")

    # This app no longer loads an in-process GGUF; inference is via Ollama REST
    state.model = None
    state.model_loaded = False

    # Check for mock mode
    state.mock_mode = os.getenv("MOCK_LLM", "false").lower() == "true"
    
    if state.mock_mode:
        logging.info("Running in MOCK mode - no Ollama connection required")
        state.model_loaded = True
    else:
        try:
            
            resp = requests.get(f"{state.ollama_base_url}/api/tags", timeout=3)
            resp.raise_for_status()
            tags = resp.json().get("models", []) or resp.json().get("data", [])
            
            names = {t.get("name") or t.get("model") for t in tags if isinstance(t, dict)}
            state.model_loaded = state.model_name in names

            if state.model_loaded:
                logging.info(f"Ollama ready with model '{state.model_name}' at {state.ollama_base_url}.")
            else:
                logging.warning(
                    f"Ollama reachable but model '{state.model_name}' not found in tags: {sorted(names)}. "
                    f"Create or pull the model, then restart the API."
                )
        except Exception as e:
            logging.error(f"Ollama probe failed: {e}")
            logging.info("To run in mock mode, set MOCK_LLM=true in your .env file")
            state.model_loaded = False
    yield
    state.model_loaded = False
    state.model = None
    logging.info("Model state cleared on shutdown.")


app = FastAPI(title="AI Coding Mentor API", lifespan=lifespan)

from app.routes import users, roadmaps, ask, health  # noqa: E402
try:
    from app.routes import execute  # noqa: E402
    app.include_router(execute.router)
except ImportError:
    logging.warning("Execute route not found - code execution will not be available")

app.include_router(users.router)
app.include_router(roadmaps.router)
app.include_router(ask.router)
app.include_router(health.router)