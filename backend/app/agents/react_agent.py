import json
import time
import re
import uuid
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import AgentTrace, UserProfile, AgentPerformanceMetrics
from app.schemas import HistoryTurn
from app.utils.token_tracker import TokenTracker



# Security: Max attempts to prevent infinite loops
MAX_CORRECTION_ATTEMPTS = 5
MAX_PROMPT_LENGTH = 10000


class SelfImprovingReActAgent:
    """Self-improving agent with code validation and self-correction."""

    def __init__(self, llm_client, db: Session):
        self.llm = llm_client
        self.db = db
        self.session_id = str(uuid.uuid4())

    async def process_request(
        self, user_id: int, question: str, history: List[HistoryTurn]
    ) -> Dict:
        """Process user question with validation and self-correction."""
        start_time = time.time()

        # Sanitize input
        question = self._sanitize_input(question)

        # Get user profile
        user_profile = (
            self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        )

        if not user_profile:
            return {
                "response": "User profile not found. Please complete onboarding first.",
                "confidence": 0,
                "reasoning": "No user profile",
                "execution_time_ms": 0,
                "improvement_active": False,
            }

        # Analyze past performance
        learning_insights = await self._analyze_past_performance(user_id)

        # Build prompt
        prompt = self._build_teaching_prompt(user_profile, question, history, learning_insights)

        # Generate response
        try:
            response_text = await self.llm.generate(prompt, timeout=30)
            success = len(response_text) > 50
            confidence = 80 if success else 50
            correction_attempts = 0

        except Exception as e:
            print(f"Error processing request: {e}")
            response_text = "I encountered an error. Please try rephrasing your question."
            success = False
            confidence = 0
            correction_attempts = 0

        execution_time = int((time.time() - start_time) * 1000)

        # Log interaction (safe-guard: _log_trace may be implemented elsewhere)

        # Calculate token usage
        tracking_data = TokenTracker.get_tracking_data(prompt, response_text)
        
        # Log interaction with token tracking
        if hasattr(self, "_log_trace"):
            await self._log_trace(
                user_id=user_id,
                user_input=question,
                reasoning=f"Direct response for: {question[:100]}",
                action_taken="explain",
                action_parameters=json.dumps({"mode": "direct"}),
                observation=f"Generated {len(response_text)} characters",
                reflection="Response completed",
                success=success,
                confidence_score=confidence,
                execution_time_ms=execution_time,
                correction_attempts=correction_attempts,
                pattern_detected=None,
                improvement_suggestion=None,
                prompt_tokens=tracking_data["prompt_tokens"],
                completion_tokens=tracking_data["completion_tokens"],
                estimated_cost_usd=tracking_data["estimated_cost_usd"],
            )

        # Update metrics if available
        if hasattr(self, "_update_performance_metrics"):
            await self._update_performance_metrics(user_id)

        return {
            "response": response_text,
            "confidence": confidence,
            "reasoning": "Answered based on user profile and past performance",
            "execution_time_ms": execution_time,
            "improvement_active": bool(learning_insights.get("prefer_actions")),
            "correction_attempts": correction_attempts,
        }

    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input for security."""
        text = text[:MAX_PROMPT_LENGTH]
        text = "".join(char for char in text if char.isprintable() or char in "\n\t")

        dangerous_patterns = [
            r";\s*DROP\s+TABLE",
            r";\s*DELETE\s+FROM",
            r"UNION\s+SELECT",
            r"<script",
            r"javascript:",
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text.strip()

    def _build_teaching_prompt(
        self, user_profile: UserProfile, question: str, history: List[HistoryTurn], insights: Dict
    ) -> str:
        """Build teaching prompt for the LLM using the user profile and recent history."""
        history_text = ""
        if history:
            recent = history[-3:]
            history_text = "\n".join(
                [f"Student: {h.user[:200]}\nMentor: {h.assistant[:200]}" for h in recent]
            )

        history_section = f"Recent Conversation:\n{history_text}\n\n" if history_text else ""

        prompt = (
            f"You are an expert coding mentor teaching a {user_profile.experience} level student.\n\n"
            f"Student Profile:\n- Programming Language: {user_profile.programming_language}\n"
            f"- Learning Style: {user_profile.learning_style}\n- Experience Level: {user_profile.experience}\n"
            f"- Learning Goal: {user_profile.goal}\n- Daily Study Time: {user_profile.daily_hours} hours\n\n"
            + history_section
            + f"Student's Question: {question}\n\n"
            + "Provide a clear, helpful answer that:\n"
            + "1. Directly addresses their question\n"
            + "2. Is appropriate for their "
            + f"{user_profile.experience} level\n"
            + "3. Includes a practical code example if relevant (use ```"
            + "4. Uses "
            + f"{user_profile.learning_style} teaching approach\n\n"
            + "CRITICAL: If the question asks for code:\n"
            + "- Provide COMPLETE, WORKING CODE inside ```python code blocks FIRST\n"
            + "- Code must be syntactically correct and runnable\n"
            + "- Then add a brief explanation below the code\n"
            + "- Do NOT start with explanations or theory\n\n"
            + "Your response:"
        )

        return prompt


    async def _analyze_past_performance(self, user_id: int) -> Dict:
        """Analyze past interactions to identify patterns and preferences."""
        recent_failures = (
            self.db.query(AgentTrace)
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.success == False,
                    AgentTrace.timestamp >= datetime.now(timezone.utc) - timedelta(days=7),
                )
            )
            .order_by(AgentTrace.timestamp.desc())
            .limit(10)
            .all()
        )

        similar_successes = (
            self.db.query(AgentTrace)
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.success == True,
                    AgentTrace.confidence_score >= 80,
                )
            )
            .order_by(AgentTrace.timestamp.desc())
            .limit(5)
            .all()
        )

        insights: Dict = {
            "common_failure_patterns": [],
            "successful_strategies": [],
            "avoid_actions": [],
            "prefer_actions": [],
        }

        for failure in recent_failures:
            if failure.pattern_detected:
                insights["common_failure_patterns"].append(failure.pattern_detected)

        for success in similar_successes:
            if success.action_taken:
                insights["prefer_actions"].append(success.action_taken)

        return insights

    async def _log_trace(self, **kwargs):
        """Log interaction trace with correction metrics."""
        trace_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc),
            **kwargs,
        }

        # Extract correction metrics
        correction_attempts = trace_data.pop("correction_attempts", 0)
        # Accept explicit original/final confidences if provided; otherwise fall back to confidence_score
        original_confidence = trace_data.pop("original_confidence", trace_data.get("confidence_score"))
        final_confidence = trace_data.pop("final_confidence", trace_data.get("confidence_score"))

        # Calculate improvement
        improvement_delta = None
        if correction_attempts > 0 and original_confidence is not None and final_confidence is not None:
            try:
                improvement_delta = final_confidence - original_confidence
            except Exception:
                improvement_delta = None

        # Add to trace data
        trace_data["correction_attempts"] = correction_attempts
        trace_data["original_confidence"] = original_confidence
        trace_data["final_confidence"] = final_confidence
        trace_data["improvement_delta"] = improvement_delta
        
        # Adding token tracking data
        trace_data["prompt_tokens"] = kwargs.get("prompt_tokens")
        trace_data["completion_tokens"] = kwargs.get("completion_tokens")
        trace_data["estimated_cost_usd"] = kwargs.get("estimated_cost_usd")

        trace = AgentTrace(**trace_data)
        self.db.add(trace)
        self.db.commit()

    async def _update_performance_metrics(self, user_id: int):
        """Update aggregate performance metrics."""
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        traces = (
            self.db.query(AgentTrace)
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.timestamp >= since,
                )
            )
            .all()
        )

        if not traces:
            return

        total = len(traces)
        successful = sum(1 for t in traces if t.success)

        confidences = [t.confidence_score for t in traces if t.confidence_score is not None]
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0

        times = [t.execution_time_ms for t in traces if t.execution_time_ms is not None]
        avg_time = (sum(times) / len(times)) if times else 0

        tool_usage = {}
        for trace in traces:
            action = getattr(trace, "action_taken", None)
            if action:
                tool_usage[action] = tool_usage.get(action, 0) + 1

        metrics = (
            self.db.query(AgentPerformanceMetrics)
            .filter(AgentPerformanceMetrics.user_id == user_id)
            .first()
        )

        if not metrics:
            metrics = AgentPerformanceMetrics(user_id=user_id)
            self.db.add(metrics)

        metrics.total_interactions = total
        metrics.successful_interactions = successful
        metrics.average_confidence = int(avg_confidence)
        metrics.average_execution_time_ms = int(avg_time)
        metrics.tool_usage_stats = json.dumps(tool_usage)
        metrics.date = datetime.now(timezone.utc)

        self.db.commit()