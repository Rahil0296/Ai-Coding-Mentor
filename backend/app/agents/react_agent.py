import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from app.models import AgentTrace, AgentPerformanceMetrics, UserProfile
from app.schemas import HistoryTurn


class SelfImprovingReActAgent:
    """
    Simplified working agent that actually answers user questions.
    Logs interactions for future learning analysis.
    """
    
    def __init__(self, llm_client, db: Session):
        self.llm = llm_client
        self.db = db
        self.session_id = str(uuid.uuid4())
        
    async def process_request(self, user_id: int, question: str, history: List[HistoryTurn]) -> Dict:
        """Process user question and return response with metrics."""
        start_time = time.time()
        
        # Get user profile
        user_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        
        if not user_profile:
            return {
                "response": "User profile not found. Please complete onboarding first.",
                "confidence": 0,
                "reasoning": "No user profile",
                "execution_time_ms": 0,
                "improvement_active": False
            }
        
        # Analyze past performance
        learning_insights = await self._analyze_past_performance(user_id)
        
        # Build context-aware prompt that includes the actual question
        prompt = self._build_teaching_prompt(user_profile, question, history, learning_insights)
        
        # Get response from LLM
        try:
            response_text = await self.llm.generate(prompt, timeout=30)
            success = len(response_text) > 50
            confidence = 85 if success else 50
        except Exception as e:
            response_text = f"I encountered an error. Please try rephrasing your question."
            success = False
            confidence = 0
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # Log the interaction
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
            pattern_detected=None,
            improvement_suggestion=None
        )
        
        # Update metrics
        await self._update_performance_metrics(user_id)
        
        return {
            "response": response_text,
            "confidence": confidence,
            "reasoning": f"Answered based on user profile and past performance",
            "execution_time_ms": execution_time,
            "improvement_active": bool(learning_insights.get("prefer_actions"))
        }
    
    def _build_teaching_prompt(self, user_profile: UserProfile, question: str, 
                               history: List[HistoryTurn], insights: Dict) -> str:
        """Build an effective teaching prompt."""
        
        # Format history
        history_text = ""
        if history:
            recent = history[-3:]
            history_text = "\n".join([
                f"Student: {h.user}\nMentor: {h.assistant}" 
                for h in recent
            ])
        
        # Build history section separately to avoid f-string backslash issue
        history_section = f"Recent Conversation:\n{history_text}\n\n" if history_text else ""
        
        # Build prompt
        prompt = f"""You are an expert coding mentor teaching a {user_profile.experience} level student.

Student Profile:
- Programming Language: {user_profile.programming_language}
- Learning Style: {user_profile.learning_style}
- Experience Level: {user_profile.experience}
- Learning Goal: {user_profile.goal}
- Daily Study Time: {user_profile.daily_hours} hours

{history_section}Student's Question: {question}

Provide a clear, helpful answer that:
1. Directly addresses their question
2. Is appropriate for their {user_profile.experience} level
3. Includes a practical code example if relevant
4. Uses {user_profile.learning_style} teaching approach

Your response:"""
        
        return prompt
    
    async def _analyze_past_performance(self, user_id: int) -> Dict:
        """Analyze past interactions to identify patterns."""
        
        recent_failures = self.db.query(AgentTrace).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.success == False,
                AgentTrace.timestamp >= datetime.utcnow() - timedelta(days=7)
            )
        ).order_by(AgentTrace.timestamp.desc()).limit(10).all()
        
        similar_successes = self.db.query(AgentTrace).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.success == True,
                AgentTrace.confidence_score >= 80
            )
        ).order_by(AgentTrace.timestamp.desc()).limit(5).all()
        
        insights = {
            "common_failure_patterns": [],
            "successful_strategies": [],
            "avoid_actions": [],
            "prefer_actions": []
        }
        
        for failure in recent_failures:
            if failure.pattern_detected:
                insights["common_failure_patterns"].append(failure.pattern_detected)
        
        for success in similar_successes:
            insights["prefer_actions"].append(success.action_taken)
        
        return insights
    
    async def _log_trace(self, **kwargs):
        """Log interaction trace."""
        trace = AgentTrace(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        self.db.add(trace)
        self.db.commit()
    
    async def _update_performance_metrics(self, user_id: int):
        """Update aggregate performance metrics."""
        since = datetime.utcnow() - timedelta(hours=24)
        
        traces = self.db.query(AgentTrace).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= since
            )
        ).all()
        
        if not traces:
            return
        
        total = len(traces)
        successful = sum(1 for t in traces if t.success)
        avg_confidence = sum(t.confidence_score for t in traces) / total
        avg_time = sum(t.execution_time_ms for t in traces) / total
        
        tool_usage = {}
        for trace in traces:
            action = trace.action_taken
            tool_usage[action] = tool_usage.get(action, 0) + 1
        
        metrics = self.db.query(AgentPerformanceMetrics).filter(
            AgentPerformanceMetrics.user_id == user_id
        ).first()
        
        if not metrics:
            metrics = AgentPerformanceMetrics(user_id=user_id)
            self.db.add(metrics)
        
        metrics.total_interactions = total
        metrics.successful_interactions = successful
        metrics.average_confidence = int(avg_confidence)
        metrics.average_execution_time_ms = int(avg_time)
        metrics.tool_usage_stats = json.dumps(tool_usage)
        metrics.date = datetime.utcnow()
        
        self.db.commit()