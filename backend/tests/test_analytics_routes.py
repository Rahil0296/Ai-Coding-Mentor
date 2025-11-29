"""
Tests for Analytics Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analytics_invalid_user():
    """Test analytics with invalid user_id returns 404."""
    response = client.get("/analytics/99999")
    assert response.status_code == 404


def test_analytics_negative_user():
    """Test analytics with negative user_id returns 400."""
    response = client.get("/analytics/-1")
    assert response.status_code == 400


def test_token_usage_invalid_user():
    """Test token usage with invalid user returns 404."""
    response = client.get("/analytics/99999/token-usage")
    assert response.status_code == 404


def test_learning_velocity_invalid_user():
    """Test velocity with invalid user returns 404."""
    response = client.get("/analytics/99999/velocity")
    assert response.status_code == 404


def test_question_search_invalid_user():
    """Test search with invalid user returns 404."""
    response = client.get("/analytics/99999/search?q=test")
    assert response.status_code == 404


def test_question_search_short_query():
    """Test search with too short query returns 422 validation error."""
    response = client.get("/analytics/1/search?q=ab")
    assert response.status_code == 422  # Validation error


def test_daily_tip_endpoint():
    """Test daily tip endpoint returns tip."""
    response = client.get("/ask/daily-tip")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "daily_tip" in data
    assert "date" in data
    assert "tip_id" in data