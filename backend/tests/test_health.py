import requests

def test_health_endpoint():
    resp = requests.get("http://127.0.0.1:8000/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True