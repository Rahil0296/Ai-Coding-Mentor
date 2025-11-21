from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, desc, case
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime, timezone
import re

from app.models import User, UserProfile, AgentTrace, ConversationHistory
from app.analytics_schemas import (
    AnalyticsResponse, 
    DailyActivity, 
    TopicFrequency, 
    TeachingModeStats, 
    StreakInfo
)


class AnalyticsService:
    """
    Service layer for analytics calculations.
    All queries use parameterized statements via ORM to prevent SQL injection.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._validate_db_session(db)
    
    def _validate_db_session(self, db: Session) -> None:
        """Ensure database session is valid."""
        if db is None:
            raise ValueError("Database session cannot be None")
    
    def _validate_user_id(self, user_id: int) -> None:
        """
        Validate user_id is positive integer and user exists.
        
        Security: Prevents negative IDs, injection attempts, and unauthorized access.
        """
        if not isinstance(user_id, int):
            raise ValueError(f"user_id must be an integer, got {type(user_id)}")
        
        if user_id <= 0:
            raise ValueError(f"user_id must be positive, got {user_id}")
        
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} does not exist")
    
    def get_user_analytics(self, user_id: int, days_back: int = 30) -> AnalyticsResponse:
        """
        Calculate comprehensive analytics for a user.
        
        Args:
            user_id: User ID (validated)
            days_back: Number of days to analyze (max 90 for performance)
        
        Returns:
            AnalyticsResponse with all metrics
        
        Raises:
            ValueError: If user_id invalid or user doesn't exist
        """
        # Security: Validate inputs
        self._validate_user_id(user_id)
        days_back = min(max(1, days_back), 90)  # Clamp between 1-90 days
        
        # Calculate all metrics
        total_questions = self._get_total_questions(user_id)
        questions_this_week = self._get_questions_in_period(user_id, days=7)
        questions_today = self._get_questions_in_period(user_id, days=1)
        
        success_rate = self._calculate_success_rate(user_id)
        avg_confidence = self._calculate_avg_confidence(user_id)
        avg_response_time = self._calculate_avg_response_time(user_id)
        
        daily_activity = self._get_daily_activity(user_id, days_back=days_back)
        confidence_trend = self._get_confidence_trend(user_id, days_back=days_back)
        
        top_topics = self._extract_top_topics(user_id, limit=10)
        teaching_mode_stats = self._get_teaching_mode_stats(user_id)
        
        streak_info = self._calculate_streak(user_id)
        learning_time = self._estimate_learning_time(user_id)
        
        return AnalyticsResponse(
            user_id=user_id,
            total_questions=total_questions,
            questions_this_week=questions_this_week,
            questions_today=questions_today,
            success_rate=success_rate,
            avg_confidence_score=avg_confidence,
            avg_response_time_ms=avg_response_time,
            daily_activity=daily_activity,
            confidence_trend=confidence_trend,
            top_topics=top_topics,
            teaching_mode_usage=teaching_mode_stats,
            streak=streak_info,
            total_learning_time_hours=learning_time
        )
    
    def _get_total_questions(self, user_id: int) -> int:
        """Get total number of questions asked by user."""
        count = self.db.query(func.count(AgentTrace.id))\
            .filter(AgentTrace.user_id == user_id)\
            .scalar()
        return count or 0
    
    def _get_questions_in_period(self, user_id: int, days: int) -> int:
        """Get questions asked in last N days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        count = self.db.query(func.count(AgentTrace.id))\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.timestamp >= cutoff_date
                )
            )\
            .scalar()
        return count or 0
    
    def _calculate_success_rate(self, user_id: int) -> float:
        """
        Calculate success rate as percentage.
        
        Security: Protected against division by zero.
        """
        total = self._get_total_questions(user_id)
        if total == 0:
            return 0.0
        
        successful = self.db.query(func.count(AgentTrace.id))\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.success == True
                )
            )\
            .scalar() or 0
        
        rate = (successful / total) * 100
        return round(rate, 2)
    
    def _calculate_avg_confidence(self, user_id: int) -> int:
        """Calculate average confidence score."""
        avg = self.db.query(func.avg(AgentTrace.confidence_score))\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.confidence_score.isnot(None)
                )
            )\
            .scalar()
        
        return int(avg) if avg else 0
    
    def _calculate_avg_response_time(self, user_id: int) -> int:
        """Calculate average response time in milliseconds."""
        avg = self.db.query(func.avg(AgentTrace.execution_time_ms))\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.execution_time_ms.isnot(None)
                )
            )\
            .scalar()
        
        return int(avg) if avg else 0
    
    def _get_daily_activity(self, user_id: int, days_back: int = 30) -> List[DailyActivity]:
        """
        Get daily question counts and average confidence.
        
        Returns up to days_back days of data.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Query grouped by date
        results = self.db.query(
            func.date(AgentTrace.timestamp).label('date'),
            func.count(AgentTrace.id).label('count'),
            func.avg(AgentTrace.confidence_score).label('avg_conf')
        ).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= cutoff_date
            )
        ).group_by(
            func.date(AgentTrace.timestamp)
        ).order_by(
            desc('date')
        ).limit(days_back).all()
        
        # Convert to schema
        activities = []
        for row in results:
            activities.append(DailyActivity(
                date=str(row.date),
                question_count=row.count,
                avg_confidence=int(row.avg_conf) if row.avg_conf else 0
            ))
        
        return activities
    
    def _get_confidence_trend(self, user_id: int, days_back: int = 30) -> List[int]:
        """
        Get confidence scores over time (last N entries).
        
        Returns list of confidence scores in chronological order.
        """
        scores = self.db.query(AgentTrace.confidence_score)\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.confidence_score.isnot(None)
                )
            )\
            .order_by(AgentTrace.timestamp.desc())\
            .limit(days_back)\
            .all()
        
        # Reverse to get chronological order
        trend = [s[0] for s in reversed(scores) if s[0] is not None]
        return trend[:30]  # Cap at 30 points for performance
    
    def _extract_top_topics(self, user_id: int, limit: int = 10) -> List[TopicFrequency]:
        """
        Extract topics from user questions using keyword analysis.
        
        Security: Regex used only for parsing, no user input in pattern.
        Simple keyword matching - no eval() or exec().
        """
        # Get recent questions
        traces = self.db.query(AgentTrace.user_input)\
            .filter(AgentTrace.user_id == user_id)\
            .order_by(AgentTrace.timestamp.desc())\
            .limit(200)\
            .all()
        
        # Keywords to look for (safe, predefined list)
        keywords = [
            'loop', 'loops', 'for', 'while',
            'function', 'functions', 'def',
            'class', 'classes', 'object',
            'list', 'lists', 'array',
            'dict', 'dictionary', 'dictionaries',
            'string', 'strings',
            'file', 'files', 'io',
            'error', 'errors', 'exception',
            'variable', 'variables',
            'conditional', 'if', 'else'
        ]
        
        # Count occurrences (case-insensitive)
        topic_counts = {}
        for trace in traces:
            if not trace.user_input:
                continue
            
            text_lower = trace.user_input.lower()
            for keyword in keywords:
                if keyword in text_lower:
                    # Normalize topic name
                    topic_name = self._normalize_topic(keyword)
                    topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
        
        # Sort by frequency and return top N
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            TopicFrequency(topic=topic, count=count)
            for topic, count in sorted_topics
        ]
    
    def _normalize_topic(self, keyword: str) -> str:
        """Normalize keyword to standard topic name."""
        topic_map = {
            'loop': 'loops', 'for': 'loops', 'while': 'loops',
            'function': 'functions', 'def': 'functions',
            'class': 'classes', 'object': 'classes',
            'list': 'lists', 'array': 'lists',
            'dict': 'dictionaries', 'dictionary': 'dictionaries',
            'string': 'strings',
            'file': 'file I/O', 'io': 'file I/O',
            'error': 'error handling', 'exception': 'error handling',
            'variable': 'variables',
            'conditional': 'conditionals', 'if': 'conditionals', 'else': 'conditionals'
        }
        return topic_map.get(keyword, keyword)
    
    def _get_teaching_mode_stats(self, user_id: int) -> TeachingModeStats:
        """Get question counts per teaching mode."""
        # Get user's profile to access teaching mode from traces
        # Note: Teaching mode is stored in UserProfile, not traced per question
        # We'll count all questions and attribute to current mode
        # For better tracking, you'd log mode in AgentTrace
        
        # For now, return total count under current mode
        total = self._get_total_questions(user_id)
        
        profile = self.db.query(UserProfile)\
            .filter(UserProfile.user_id == user_id)\
            .first()
        
        current_mode = profile.teaching_mode if profile else "guided"
        
        # Initialize all modes to 0
        stats = {"guided": 0, "debug_practice": 0, "perfect": 0}
        
        # Assign total to current mode (limitation: no historical mode tracking)
        if current_mode in stats:
            stats[current_mode] = total
        
        return TeachingModeStats(**stats)
    
    def _calculate_streak(self, user_id: int) -> StreakInfo:
        """
        Calculate learning streak (consecutive days with activity).
        
        """
        # Get all distinct dates with activity
        dates = self.db.query(
            func.date(AgentTrace.timestamp).label('activity_date')
        ).filter(
            AgentTrace.user_id == user_id
        ).distinct()\
        .order_by(desc('activity_date'))\
        .all()
        
        if not dates:
            return StreakInfo(
                current_streak_days=0,
                longest_streak_days=0,
                last_activity_date=None
            )
        
        # Convert to list of dates
        activity_dates = [d.activity_date for d in dates]
        last_activity = str(activity_dates[0])
        
        # Calculate current streak
        current_streak = 1
        today = datetime.now(timezone.utc).date()
        
        # Check if activity is recent (today or yesterday)
        days_since_last = (today - activity_dates[0]).days
        if days_since_last > 1:
            current_streak = 0
        else:
            # Count consecutive days backwards from most recent
            for i in range(len(activity_dates) - 1):
                diff = (activity_dates[i] - activity_dates[i + 1]).days
                if diff == 1:
                    current_streak += 1
                else:
                    break
        
        # Calculate longest streak
        longest_streak = 1
        temp_streak = 1
        
        for i in range(len(activity_dates) - 1):
            diff = (activity_dates[i] - activity_dates[i + 1]).days
            if diff == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return StreakInfo(
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            last_activity_date=last_activity
        )
    
    def _estimate_learning_time(self, user_id: int) -> float:
        """
        Estimate total learning time based on response times.
        
        Assumes user spends avg_response_time per question.
        Returns hours (float).
        """
        total_ms = self.db.query(func.sum(AgentTrace.execution_time_ms))\
            .filter(
                and_(
                    AgentTrace.user_id == user_id,
                    AgentTrace.execution_time_ms.isnot(None)
                )
            )\
            .scalar()
        
        if not total_ms:
            return 0.0
        
        # Convert ms to hours
        hours = total_ms / (1000 * 60 * 60)
        return round(hours, 2)
    
    def search_past_questions(self, user_id: int, search_query: str, limit: int = 5) -> List[Dict]:
        
        # Validate inputs
        self._validate_user_id(user_id)
        
        if not search_query or len(search_query.strip()) < 3:
            raise ValueError("Search query must be at least 3 characters")
        
        search_query = search_query.lower().strip()
        
        # Get all user's questions
        traces = self.db.query(AgentTrace)\
            .filter(AgentTrace.user_id == user_id)\
            .order_by(AgentTrace.timestamp.desc())\
            .limit(200)\
            .all()
        
        if not traces:
            return []
        
        # Extract keywords from search query
        search_keywords = set(re.findall(r'\w+', search_query))
        
        # Score and rank results
        results = []
        for trace in traces:
            if not trace.user_input:
                continue
            
            question_lower = trace.user_input.lower()
            
            question_keywords = set(re.findall(r'\w+', question_lower))
            
            # Calculate match score
            common_keywords = search_keywords & question_keywords
            if not common_keywords:
                continue
            
            # Score based on keyword overlap
            score = len(common_keywords) / max(len(search_keywords), len(question_keywords))
            
            # Boost exact phrase matches
            if search_query in question_lower:
                score += 0.5
            
            now = datetime.now(timezone.utc)
            trace_time = trace.timestamp
            
            if trace_time.tzinfo is None: 
                trace_time = trace_time.replace(tzinfo=timezone.utc)
            
            days_ago = (now - trace_time).days
            
            results.append({
                "question": trace.user_input,
                "timestamp": trace.timestamp.isoformat(),
                "days_ago": days_ago,
                "confidence": trace.confidence_score or 0,
                "success": trace.success or False,
                "match_score": round(score, 2),
                "matched_keywords": list(common_keywords)
            })
        
        results.sort(key=lambda x: x["match_score"], reverse=True)
        
        return results[:limit]