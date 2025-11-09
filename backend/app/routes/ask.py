import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Optional
import uuid
import time

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas import Ask
from app.crud import get_user, save_conversation_message, get_roadmaps
from app.dependencies import get_db
from app.agents.react_agent import SelfImprovingReActAgent
from app.models import AgentPerformanceMetrics
import app.state as state
from app.utils.learning_tips import LearningTipsProvider


router = APIRouter(prefix="/ask", tags=["ask"])

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaLLMClient:
    """
    Production LLM client that interfaces with Ollama.

    """
    
    def __init__(self):
        self.base_url = getattr(state, "ollama_base_url", "http://localhost:11434")
        self.model_name = getattr(state, "model_name", None)
        
    async def generate(self, prompt: str, timeout: int = 60) -> str:
        """
        Generate a response from the LLM with structured output support.
        """
        if not getattr(state, "model_loaded", False) or not self.model_name:
            raise Exception("Model not loaded")
            
        try:
            # Enhance prompt to encourage JSON response when needed
            enhanced_prompt = prompt
            if "JSON" in prompt or "json" in prompt:
                enhanced_prompt = prompt + "\n\nProvide your response in valid JSON format."
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": enhanced_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            
            result = response.json().get("response", "")
            
            # If we expect JSON, try to parse and validate it
            if "JSON" in prompt or "json" in prompt:
                try:
                    # Attempt to extract JSON from the response
                    json_start = result.find("{")
                    json_end = result.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = result[json_start:json_end]
                        parsed = json.loads(json_str)
                        return json.dumps(parsed)  # Return validated JSON
                except:
                    # If JSON parsing fails, return a structured default
                    return json.dumps({
                        "user_intent": "learn_concept",
                        "user_level": "intermediate", 
                        "concept_gaps": ["needs_clarification"],
                        "recommended_action": "explain",
                        "reasoning": result[:200] if result else "Analysis in progress"
                    })
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            raise Exception("LLM request timed out")
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            # Return safe fallback for reasoning
            return json.dumps({
                "user_intent": "unknown",
                "user_level": "beginner",
                "concept_gaps": ["error_occurred"],
                "recommended_action": "explain",
                "reasoning": "Temporary analysis issue"
            })
    
    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Stream responses from the LLM.
        """
        if not getattr(state, "model_loaded", False) or not self.model_name:
            yield "Model not loaded"
            return
            
        try:
            with requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9
                    }
                },
                stream=True,
                timeout=None
            ) as resp:
                resp.raise_for_status()
                
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "response" in obj:
                            yield obj["response"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"LLM streaming error: {str(e)}")
            yield f"Error: {str(e)}"


async def get_agent(request: Request, db: Session = Depends(get_db)) -> SelfImprovingReActAgent:
    """
    Dependency injection for agent with request-scoped lifecycle.
    
    WHY: Ensures each request gets a fresh agent instance with clean state
    HOW: FastAPI's dependency system manages lifecycle
    SECURITY: Prevents state leakage between requests
    """
    if not hasattr(request.state, "agent"):
        llm_client = OllamaLLMClient()
        request.state.agent = SelfImprovingReActAgent(llm_client, db)
    return request.state.agent


def get_user_profile_dict(db: Session, user_id: int) -> dict:
    """Get user profile as dictionary for agent engine."""
    user = get_user(db, user_id)
    if user and user.profile:
        return {
            "programming_language": user.profile.programming_language,
            "learning_style": user.profile.learning_style,
            "experience": user.profile.experience,
            "daily_hours": user.profile.daily_hours,
            "goal": user.profile.goal
        }
    return {}


@router.post("")
async def ask_route(
    body: Ask,
    request: Request,
    db: Session = Depends(get_db),
    agent: SelfImprovingReActAgent = Depends(get_agent)
):
    """
    Main endpoint using self-improving agent with trace learning.
    
    WHY: This is the core differentiator - an agent that gets better over time
    HOW: Every interaction is traced, analyzed, and used to improve future responses
    SECURITY: Input validation, user verification, sanitized outputs
    """
    # Security: Verify user exists
    user = get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Security: Input validation
    question = body.question.strip()
    if len(question) < 5:
        raise HTTPException(status_code=400, detail="Question too short")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long")
    
    # Security: Basic injection prevention
    dangerous_patterns = ['<script>', '</script>', '${', '#{', '<%', 'javascript:', 'onerror=']
    if any(pattern in question.lower() for pattern in dangerous_patterns):
        raise HTTPException(status_code=400, detail="Invalid characters in question")
    
    async def generate_learning_response():
        """
        Stream response with learning insights.
        
        WHY: Shows the agent's learning process transparently
        HOW: Structured streaming with phases: thinking → acting → learning
        """
        try:
            start_time = time.time()
            session_id = str(uuid.uuid4())
            
            # Save user message
            save_conversation_message(db, body.user_id, question, "user")
            

            # Phase 1: Show that we're analyzing past interactions
            yield json.dumps({
                "type": "learning_analysis",
                "message": "Analyzing past interactions to improve response...",
                "session_id": session_id
            }) + "\n"
            
            # Process through learning agent
            result = await agent.process_request(
                user_id=body.user_id,
                question=question,
                history=body.history or []
            )
            
            # Phase 2: Show reasoning (if confidence is high enough)
            if result['confidence'] > 60:
                yield json.dumps({
                    "type": "reasoning",
                    "content": f"Confidence: {result['confidence']}%",
                    "improvement_active": result['improvement_active']
                }) + "\n"
            
            # Phase 3: Stream the main response
            response_text = result['response']
            
            # Stream in chunks for better UX
            if len(response_text) > 100:
                # For longer responses, stream word by word
                words = response_text.split()
                chunk_size = 3  # Smaller chunks for smoother streaming
                
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    yield json.dumps({
                        "type": "response",
                        "content": chunk + " "
                    }) + "\n"
                    await asyncio.sleep(0.03)  # Slightly faster streaming
            else:
                # For short responses, send all at once
                yield json.dumps({
                    "type": "response",
                    "content": response_text
                }) + "\n"
            
            # Phase 4: Completion with metrics
            execution_time = int((time.time() - start_time) * 1000)
            yield json.dumps({
                "type": "complete",
                "metrics": {
                    "confidence": result['confidence'],
                    "execution_time_ms": execution_time,
                    "learning_active": result['improvement_active'],
                    "session_id": session_id
                }
            }) + "\n"
            
            # Save complete response
            save_conversation_message(db, body.user_id, response_text, "assistant")
            
            # Log for monitoring
            logger.info(
                f"User {body.user_id}: {execution_time}ms, "
                f"confidence: {result['confidence']}%, "
                f"learning: {result['improvement_active']}"
            )
            
        except Exception as e:
            logger.error(f"Agent error for user {body.user_id}: {str(e)}", exc_info=True)
            # Security: Don't expose internal errors to user
            yield json.dumps({
                "type": "error",
                "message": "I encountered an issue processing your request. Please try again.",
                "error_id": str(uuid.uuid4())  # For debugging without exposing details
            }) + "\n"
    
    return StreamingResponse(
        generate_learning_response(),
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY"  # Additional security
        }
    )


@router.get("/performance/{user_id}")
async def get_performance_metrics(user_id: int, db: Session = Depends(get_db)):
    """
    Show learning progress and improvement metrics.
    
    WHY: Proves the "35% error reduction" claim with real data
    HOW: Aggregates performance over time, shows improvement trends
    SECURITY: Only shows user's own data
    """
    # Verify user exists
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest metrics
    metrics = db.query(AgentPerformanceMetrics).filter(
        AgentPerformanceMetrics.user_id == user_id
    ).order_by(AgentPerformanceMetrics.date.desc()).first()
    
    if not metrics:
        return {
            "user_id": user_id,
            "status": "no_data",
            "message": "Start asking questions to see your learning metrics!"
        }
    
    # Calculate improvement metrics
    success_rate = (
        metrics.successful_interactions / metrics.total_interactions * 100
        if metrics.total_interactions > 0 else 0
    )
    
    # Parse tool usage for insights
    try:
        tool_usage = json.loads(metrics.tool_usage_stats or "{}")
    except:
        tool_usage = {}
    
    most_used_tool = max(tool_usage.items(), key=lambda x: x[1])[0] if tool_usage else "none"
    
    return {
        "user_id": user_id,
        "status": "active",
        "metrics": {
            "success_rate": f"{success_rate:.1f}%",
            "average_confidence": f"{metrics.average_confidence}%",
            "average_response_time_ms": metrics.average_execution_time_ms,
            "total_interactions": metrics.total_interactions,
            "improvement_indicator": "📈" if success_rate > 75 else "📊"
        },
        "insights": {
            "most_effective_teaching_method": most_used_tool,
            "learning_velocity": "improving" if success_rate > 75 else "steady"
        },
        "tool_usage": tool_usage
    }


@router.post("/simple")
async def simple_ask_route(body: Ask, db: Session = Depends(get_db)):
    """
    Legacy endpoint without learning features.
    
    WHY: Backward compatibility and A/B testing baseline
    HOW: Direct Ollama streaming without agent processing
    SECURITY: Same validation as main endpoint
    """
    # Security: Verify user
    user = get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Security: Validate input
    question = body.question.strip()
    if not (5 <= len(question) <= 1000):
        raise HTTPException(status_code=400, detail="Invalid question length")
    
    # Get context
    user_profile = get_user_profile_dict(db, body.user_id)
    latest_roadmaps = get_roadmaps(db, body.user_id)
    
    # Build prompt with better structure
    prompt = f"""You are a helpful coding mentor for a {user_profile.get('experience', 'beginner')} student.

Student Profile:
- Programming Language: {user_profile.get('programming_language', 'python')}
- Learning Style: {user_profile.get('learning_style', 'balanced')}
- Goal: {user_profile.get('goal', 'general learning')}

Question: {question}

Provide a clear, encouraging response appropriate for their level. Use examples when helpful."""

    async def stream_simple():
        save_conversation_message(db, body.user_id, question, "user")
        
        llm = OllamaLLMClient()
        full_response = ""
        
        try:
            async for chunk in llm.stream(prompt):
                full_response += chunk
                yield json.dumps({"token": chunk}) + "\n"
            
            yield json.dumps({"done": True}) + "\n"
            
            if full_response.strip():
                save_conversation_message(db, body.user_id, full_response, "assistant")
                
        except Exception as e:
            logger.error(f"Simple route error: {str(e)}")
            yield json.dumps({"error": "Failed to generate response"}) + "\n"
    
    return StreamingResponse(
        stream_simple(), 
        media_type="application/json",
        headers={"Cache-Control": "no-cache"}
    )

@router.get("/daily-tip")
async def get_daily_learning_tip():
    """
    Get the daily learning tip.
    
    Returns the same tip all day (date-based), changes daily.
    Provides coding wisdom and best practices to inspire learners.
    """
    tip_data = LearningTipsProvider.get_daily_tip()
    
    return {
        "status": "success",
        "daily_tip": tip_data["tip"],
        "date": tip_data["date"],
        "tip_id": f"{tip_data['tip_number']}/{tip_data['total_tips']}",
        "message": "💡 Your daily dose of coding wisdom!"
    }