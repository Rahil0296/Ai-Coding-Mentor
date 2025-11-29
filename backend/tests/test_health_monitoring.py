"""
Tests for Health Monitoring Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_quick():
    """Test quick health check returns 200."""
    response = client.get("/health/quick")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()


def test_health_live():
    """Test liveness check returns 200."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert "uptime_seconds" in response.json()


def test_health_comprehensive():
    """Test comprehensive health check returns detailed status."""
    response = client.get("/health/")
    assert response.status_code in [200, 503]  # Can be unhealthy but still respond
    
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "timestamp" in data
    assert "version" in data
    
    # Check for key health checks
    checks = data.get("checks", {})
    assert "database" in checks or "ai_model" in checks or "system_resources" in checks