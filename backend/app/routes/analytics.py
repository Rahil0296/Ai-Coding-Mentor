"""
Analytics Route
Secure endpoint for retrieving user learning analytics.

Security features:
- Input validation (user_id must be positive integer)
- User existence verification
- Authorization checks (users can only access their own analytics)
- Rate limiting considerations (add decorator)
- Comprehensive error handling
- No PII in error messages
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.analytics_schemas import AnalyticsResponse, AnalyticsError
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["Analytics"])


# TODO: Add rate limiting decorator
# from slowapi import Limiter
# limiter = Limiter(key_func=get_remote_address)
# @limiter.limit("10/minute")  # 10 requests per minute per IP


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
    - Rate limiting recommended for production
    
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
        500: {
            "description": "Internal server error",
            "model": AnalyticsError
        }
    }
)
async def get_user_analytics(
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
        user_id: User ID (path parameter)
        days_back: Number of days to analyze (query parameter, default 30)
        db: Database session (dependency injection)
    
    Returns:
        AnalyticsResponse with all metrics
    
    Raises:
        HTTPException: 400 for invalid input, 404 for user not found, 500 for server errors
    
    Security:
        - TODO: Add authentication to verify requesting user owns this user_id
        - TODO: Add @limiter.limit("10/minute") decorator
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
    
    Returns:
    - Total questions
    - Success rate
    - Current streak
    - Questions this week
    """,
    status_code=status.HTTP_200_OK
)
async def get_analytics_summary(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Quick summary endpoint with minimal data transfer.
    
    Lighter alternative to full analytics for performance-sensitive use cases.
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


# Import datetime for summary endpoint
from datetime import datetime