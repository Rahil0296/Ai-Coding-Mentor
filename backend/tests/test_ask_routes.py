"""
Tests for Ask Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ask_endpoint_invalid_user():
    """Test ask endpoint with non-existent user returns 404."""
    response = client.post(
        "/ask",
        json={
            "user_id": 99999,
            "question": "How do I write a for loop?",
            "history": None
        }
    )
    assert response.status_code == 404


def test_ask_endpoint_short_question():
    """Test ask endpoint with too short question returns 400."""
    response = client.post(
        "/ask",
        json={
            "user_id": 1,
            "question": "hi",
            "history": None
        }
    )
    assert response.status_code == 400


def test_ask_endpoint_long_question():
    """Test ask endpoint with too long question returns 400."""
    response = client.post(
        "/ask",
        json={
            "user_id": 1,
            "question": "a" * 1001,  # Over 1000 chars
            "history": None
        }
    )
    assert response.status_code == 400


def test_ask_endpoint_xss_attempt():
    """Test ask endpoint blocks XSS attempts."""
    response = client.post(
        "/ask",
        json={
            "user_id": 1,
            "question": "How do I <script>alert('xss')</script> in Python?",
            "history": None
        }
    )
    assert response.status_code == 400
    assert "Invalid characters" in response.json()["detail"]


def test_performance_endpoint_invalid_user():
    """Test performance endpoint with invalid user returns 404."""
    response = client.get("/ask/performance/99999")
    assert response.status_code == 404