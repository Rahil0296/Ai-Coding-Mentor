"""
Analytics Route
Secure endpoint for retrieving user learning analytics.

Security features:
- Input validation (user_id must be positive integer)
- User existence verification
- Rate limiting (10 requests per minute for analytics, 30 for summary)
- Comprehensive error handling
- No PII in error messages
"""
from app.middleware.rate_limiting import rate_limit
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, case
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.analytics_schemas import AnalyticsResponse, AnalyticsError
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/{user_id}",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Learning Analytics",
    description="""
    Retrieve comprehensive learning analytics for a user.
    
    **Security Notes:**
    - User must exist in database
    - Returns 404 if user not found
    - All metrics are calculated from database with SQL injection protection
    - Rate limited to 10 requests per minute per IP
    
    **Metrics Included:**
    - Question counts (total, weekly, daily)
    - Success rate and confidence scores
    - Daily activity trends
    - Top topics explored
    - Teaching mode usage
    - Learning streaks
    - Estimated learning time
    
    **Performance:**
    - Query optimized for sub-second response
    - Results cached internally for 5 minutes (TODO)
    - Max 90 days of historical data
    """,
    responses={
        200: {
            "description": "Analytics successfully retrieved",
            "model": AnalyticsResponse
        },
        400: {
            "description": "Invalid user_id provided",
            "model": AnalyticsError
        },
        404: {
            "description": "User not found",
            "model": AnalyticsError
        },
        429: {
            "description": "Rate limit exceeded - too many requests"
        },
        500: {
            "description": "Internal server error",
            "model": AnalyticsError
        }
    }
)
@rate_limit("analytics")  # 10 requests per minute
async def get_user_analytics(
    request: Request,
    user_id: int,
    days_back: Optional[int] = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of days to analyze (1-90)"
    ),
    db: Session = Depends(get_db)
) -> AnalyticsResponse:
    """
    Get comprehensive analytics for a specific user.
    
    Args:
        request: FastAPI request object (for rate limiting)
        user_id: User ID (path parameter)
        days_back: Number of days to analyze (query parameter, default 30)
        db: Database session (dependency injection)
    
    Returns:
        AnalyticsResponse with all metrics
    
    Raises:
        HTTPException: 400 for invalid input, 404 for user not found, 429 for rate limit, 500 for server errors
    
    Security:
        - Rate limited to 10 requests per minute per IP address
        - TODO: Add authentication to verify requesting user owns this user_id
    """
    
    # Input validation: user_id must be positive
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid user_id",
                "detail": "user_id must be a positive integer"
            }
        )
    
    try:
        # Initialize service
        analytics_service = AnalyticsService(db)
        
        # Get analytics (service handles validation and existence check)
        analytics = analytics_service.get_user_analytics(
            user_id=user_id,
            days_back=days_back
        )
        
        return analytics
    
    except ValueError as e:
        # User not found or validation error
        error_msg = str(e)
        
        if "does not exist" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "User not found",
                    "detail": f"No user found with id {user_id}",
                    "user_id": user_id
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation error",
                    "detail": error_msg,
                    "user_id": user_id
                }
            )
    
    except Exception as e:
        # Log the actual error for debugging (not exposed to user)
        print(f"[ANALYTICS ERROR] user_id={user_id}, error={str(e)}")
        
        # Return generic error (don't leak implementation details)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "detail": "An error occurred while calculating analytics. Please try again later.",
                "user_id": user_id
            }
        )


@router.get(
    "/{user_id}/summary",
    summary="Get Quick Analytics Summary",
    description="""
    Lightweight endpoint returning only key metrics.
    Useful for dashboard widgets or mobile apps.
    
    Rate limited to 30 requests per minute per IP.
    
    Returns:
    - Total questions
    - Success rate
    - Current streak
    - Questions this week
    """,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Summary successfully retrieved"},
        400: {"description": "Invalid user_id"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
@rate_limit("analytics_summary")  # 30 requests per minute
async def get_analytics_summary(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Quick summary endpoint with minimal data transfer.
    
    Lighter alternative to full analytics for performance-sensitive use cases.
    Rate limited to 30 requests per minute per IP address.
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be positive"
        )
    
    try:
        service = AnalyticsService(db)
        
        # Get only essential metrics (faster query)
        total_q = service._get_total_questions(user_id)
        week_q = service._get_questions_in_period(user_id, days=7)
        success = service._calculate_success_rate(user_id)
        streak = service._calculate_streak(user_id)
        
        return {
            "user_id": user_id,
            "total_questions": total_q,
            "questions_this_week": week_q,
            "success_rate": success,
            "current_streak": streak.current_streak_days,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    except Exception as e:
        print(f"[ANALYTICS SUMMARY ERROR] user_id={user_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating analytics summary"
        )


@router.get(
    "/{user_id}/token-usage",
    summary="Get Token Usage & Cost Analytics",
    description="""
    Track token usage and estimated costs for LLM operations.
    
    **Metrics Included:**
    - Total tokens used (prompt + completion)
    - Estimated cost (GPT-4 equivalent pricing)
    - Average tokens per question
    - Cost efficiency trends
    - Monthly projections
    
    **Why This Matters:**
    - Production cost planning
    - Token optimization insights
    - Budget forecasting
    
    Rate limited to 30 requests per minute per IP.
    """,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Token usage analytics retrieved"},
        400: {"description": "Invalid user_id"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
@rate_limit("analytics_summary")  # 30 requests per minute
async def get_token_usage_analytics(
    request: Request,
    user_id: int,
    days_back: Optional[int] = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of days to analyze (1-90)"
    ),
    db: Session = Depends(get_db)
):
    """
    Get token usage and cost analytics for a user.
    
    Shows production-ready cost tracking and optimization insights.
    """
    from app.models import AgentTrace
    from app.utils.token_tracker import TokenTracker
    from sqlalchemy import func
    
    # Validate user_id
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be positive"
        )
    
    try:
        service = AnalyticsService(db)
        
        # Verify user exists
        service._validate_user_id(user_id)
        
        # Get date cutoff
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Query token usage data
        token_stats = db.query(
            func.sum(AgentTrace.prompt_tokens).label('total_prompt_tokens'),
            func.sum(AgentTrace.completion_tokens).label('total_completion_tokens'),
            func.sum(AgentTrace.estimated_cost_usd).label('total_cost'),
            func.avg(AgentTrace.prompt_tokens).label('avg_prompt_tokens'),
            func.avg(AgentTrace.completion_tokens).label('avg_completion_tokens'),
            func.count(AgentTrace.id).label('total_requests')
        ).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= cutoff_date,
                AgentTrace.prompt_tokens.isnot(None)
            )
        ).first()
        
        # Get daily token usage for trend
        daily_usage = db.query(
            func.date(AgentTrace.timestamp).label('date'),
            func.sum(AgentTrace.prompt_tokens + AgentTrace.completion_tokens).label('total_tokens'),
            func.sum(AgentTrace.estimated_cost_usd).label('daily_cost')
        ).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= cutoff_date,
                AgentTrace.prompt_tokens.isnot(None)
            )
        ).group_by(
            func.date(AgentTrace.timestamp)
        ).order_by(
            func.date(AgentTrace.timestamp).desc()
        ).limit(30).all()
        
        # Handle case where no token data exists yet
        if not token_stats or token_stats.total_prompt_tokens is None:
            return {
                "user_id": user_id,
                "status": "no_token_data",
                "message": "Token tracking is now active! Data will appear after your next question.",
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_tokens_per_request": 0,
                "days_analyzed": days_back,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Calculate metrics
        total_prompt = token_stats.total_prompt_tokens or 0
        total_completion = token_stats.total_completion_tokens or 0
        total_tokens = total_prompt + total_completion
        total_cost = token_stats.total_cost or 0.0
        avg_prompt = int(token_stats.avg_prompt_tokens or 0)
        avg_completion = int(token_stats.avg_completion_tokens or 0)
        total_requests = token_stats.total_requests or 0
        
        # Calculate efficiency metrics
        avg_tokens_per_request = int(total_tokens / total_requests) if total_requests > 0 else 0
        avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        
        # Monthly projection (extrapolate from period)
        days_in_data = days_back
        monthly_projection_tokens = int((total_tokens / days_in_data) * 30) if days_in_data > 0 else 0
        monthly_projection_cost = (total_cost / days_in_data) * 30 if days_in_data > 0 else 0
        
        # Format daily trends
        daily_trends = [
            {
                "date": str(day.date),
                "tokens": int(day.total_tokens or 0),
                "cost_usd": round(day.daily_cost or 0, 4)
            }
            for day in daily_usage
        ]
        
        # Token efficiency rating
        if avg_tokens_per_request < 500:
            efficiency_rating = "excellent"
            efficiency_emoji = "🌟"
        elif avg_tokens_per_request < 1000:
            efficiency_rating = "good"
            efficiency_emoji = "✅"
        elif avg_tokens_per_request < 2000:
            efficiency_rating = "moderate"
            efficiency_emoji = "⚠️"
        else:
            efficiency_rating = "needs_optimization"
            efficiency_emoji = "🔴"
        
        return {
            "user_id": user_id,
            "status": "active",
            "period": {
                "days_analyzed": days_back,
                "start_date": cutoff_date.date().isoformat(),
                "end_date": datetime.utcnow().date().isoformat()
            },
            "usage_summary": {
                "total_tokens": total_tokens,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "total_requests": total_requests,
                "total_cost_usd": round(total_cost, 4),
                "formatted_cost": TokenTracker.format_cost(total_cost),
                "formatted_tokens": TokenTracker.format_tokens(total_tokens)
            },
            "averages": {
                "avg_tokens_per_request": avg_tokens_per_request,
                "avg_prompt_tokens": avg_prompt,
                "avg_completion_tokens": avg_completion,
                "avg_cost_per_request": round(avg_cost_per_request, 4),
                "formatted_avg_cost": TokenTracker.format_cost(avg_cost_per_request)
            },
            "projections": {
                "monthly_tokens": monthly_projection_tokens,
                "monthly_cost_usd": round(monthly_projection_cost, 2),
                "formatted_monthly_cost": TokenTracker.format_cost(monthly_projection_cost),
                "yearly_cost_usd": round(monthly_projection_cost * 12, 2)
            },
            "efficiency": {
                "rating": efficiency_rating,
                "emoji": efficiency_emoji,
                "tokens_per_request": avg_tokens_per_request,
                "insight": f"Your average of {avg_tokens_per_request} tokens/request is {efficiency_rating}"
            },
            "daily_trends": daily_trends[:7],  # Last 7 days
            "cost_breakdown": {
                "input_cost_usd": round((total_prompt / 1000) * TokenTracker.INPUT_COST_PER_1K, 4),
                "output_cost_usd": round((total_completion / 1000) * TokenTracker.OUTPUT_COST_PER_1K, 4)
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except ValueError as e:
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"[TOKEN ANALYTICS ERROR] user_id={user_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating token analytics"
        )


@router.get(
    "/{user_id}/velocity",
    summary="Get Learning Velocity & Improvement Rate",
    description="""
    Track how fast you're improving as a learner.
    
    Compares this week vs last week to show:
    - Confidence score improvement
    - Success rate changes
    - Question volume trends
    - Personalized encouragement
    
    Shows you're getting better over time! 📈
    """,
    status_code=status.HTTP_200_OK
)
async def get_learning_velocity(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate learning velocity - how fast the user is improving.
    
    Compares metrics from this week vs last week.
    """
    from app.models import AgentTrace
    from sqlalchemy import func
    
    # Validate user_id
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be positive"
        )
    
    try:
        service = AnalyticsService(db)
        service._validate_user_id(user_id)
        
        now = datetime.now(timezone.utc)
        
        # Define time periods
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)
        last_week_end = this_week_start
        
        # Get this week's data
        this_week_stats = db.query(
            func.count(AgentTrace.id).label('count'),
            func.avg(AgentTrace.confidence_score).label('avg_confidence'),
            func.sum(case((AgentTrace.success == True, 1), else_=0)).label('successes')
        ).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= this_week_start,
                AgentTrace.confidence_score.isnot(None)
            )
        ).first()
        
        # Get last week's data
        last_week_stats = db.query(
            func.count(AgentTrace.id).label('count'),
            func.avg(AgentTrace.confidence_score).label('avg_confidence'),
            func.sum(case((AgentTrace.success == True, 1), else_=0)).label('successes')
        ).filter(
            and_(
                AgentTrace.user_id == user_id,
                AgentTrace.timestamp >= last_week_start,
                AgentTrace.timestamp < last_week_end,
                AgentTrace.confidence_score.isnot(None)
            )
        ).first()
        
        # Handle case where no data exists
        if not this_week_stats or this_week_stats.count == 0:
            return {
                "user_id": user_id,
                "status": "insufficient_data",
                "message": "Keep learning! We need at least a week of data to track your velocity.",
                "this_week_questions": 0,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Extract metrics
        this_week_count = this_week_stats.count or 0
        this_week_confidence = this_week_stats.avg_confidence or 0
        this_week_successes = this_week_stats.successes or 0
        this_week_success_rate = (this_week_successes / this_week_count * 100) if this_week_count > 0 else 0
        
        last_week_count = last_week_stats.count or 0 if last_week_stats else 0
        last_week_confidence = last_week_stats.avg_confidence or 0 if last_week_stats else 0
        last_week_successes = last_week_stats.successes or 0 if last_week_stats else 0
        last_week_success_rate = (last_week_successes / last_week_count * 100) if last_week_count > 0 else 0
        
        # Calculate improvements
        if last_week_confidence > 0:
            confidence_change = ((this_week_confidence - last_week_confidence) / last_week_confidence) * 100
        else:
            confidence_change = 0
        
        if last_week_success_rate > 0:
            success_rate_change = this_week_success_rate - last_week_success_rate
        else:
            success_rate_change = 0
        
        activity_change = this_week_count - last_week_count
        
        # Generate velocity rating
        if confidence_change >= 15:
            velocity_rating = "accelerating"
            emoji = "🚀"
            message = f"Amazing! You're improving {abs(int(confidence_change))}% faster than last week!"
        elif confidence_change >= 5:
            velocity_rating = "improving"
            emoji = "📈"
            message = f"Great progress! You're {abs(int(confidence_change))}% better than last week!"
        elif confidence_change >= -5:
            velocity_rating = "steady"
            emoji = "➡️"
            message = "You're maintaining consistent performance. Keep it up!"
        else:
            velocity_rating = "needs_focus"
            emoji = "💪"
            message = "Everyone has off weeks. Stay consistent and you'll bounce back!"
        
        # Activity feedback
        if activity_change > 5:
            activity_feedback = f"🔥 {activity_change} more questions than last week!"
        elif activity_change > 0:
            activity_feedback = f"✅ {activity_change} more questions than last week"
        elif activity_change == 0:
            activity_feedback = "Same activity level as last week"
        else:
            activity_feedback = f"⚠️ {abs(activity_change)} fewer questions than last week"
        
        return {
            "user_id": user_id,
            "status": "active",
            "velocity": {
                "rating": velocity_rating,
                "emoji": emoji,
                "message": message
            },
            "this_week": {
                "questions": this_week_count,
                "avg_confidence": round(this_week_confidence, 1),
                "success_rate": round(this_week_success_rate, 1)
            },
            "last_week": {
                "questions": last_week_count,
                "avg_confidence": round(last_week_confidence, 1),
                "success_rate": round(last_week_success_rate, 1)
            },
            "changes": {
                "confidence_change_percent": round(confidence_change, 1),
                "success_rate_change": round(success_rate_change, 1),
                "activity_change": activity_change,
                "activity_feedback": activity_feedback
            },
            "insight": message,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except ValueError as e:
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"[VELOCITY ERROR] user_id={user_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating learning velocity"
        )


@router.get(
    "/{user_id}/search",
    summary="Search Past Questions",
    description="""
    Search through your question history to find similar past questions.
    
    **Use Cases:**
    - "Did I ask about this before?"
    - Find related past discussions
    - Review how you learned a topic
    
    **Search Tips:**
    - Use keywords: "loop", "function", "list"
    - Minimum 3 characters
    - Returns top 5 matches by relevance
    """,
    status_code=status.HTTP_200_OK
)
async def search_past_questions(
    request: Request,
    user_id: int,
    q: str = Query(..., min_length=3, max_length=100, description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Max results"),
    db: Session = Depends(get_db)
):
    """
    Search through user's question history for similar questions.
    
    Shows when they asked similar questions before with context.
    """
    # Validate user_id
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be positive"
        )
    
    try:
        service = AnalyticsService(db)
        
        # Search past questions
        results = service.search_past_questions(
            user_id=user_id,
            search_query=q,
            limit=limit
        )
        
        # Format response
        if not results:
            return {
                "user_id": user_id,
                "search_query": q,
                "total_results": 0,
                "message": "No similar questions found. This might be your first time asking about this topic!",
                "results": [],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Generate insights
        avg_confidence = sum(r["confidence"] for r in results) / len(results) if results else 0
        most_recent = min(r["days_ago"] for r in results)
        
        if most_recent == 0:
            recency_message = "You asked about this today!"
        elif most_recent == 1:
            recency_message = "You asked about this yesterday"
        elif most_recent <= 7:
            recency_message = f"You asked about this {most_recent} days ago"
        else:
            recency_message = f"You last explored this {most_recent} days ago"
        
        return {
            "user_id": user_id,
            "search_query": q,
            "total_results": len(results),
            "message": f"Found {len(results)} similar question(s) in your history",
            "insights": {
                "recency": recency_message,
                "avg_confidence": round(avg_confidence, 1),
                "most_recent_days_ago": most_recent
            },
            "results": results,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except ValueError as e:
        error_msg = str(e)
        if "does not exist" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        print(f"[SEARCH ERROR] user_id={user_id}, query={q}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching questions"
        )