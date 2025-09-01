import pytest
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="module")
def onboard_user():
    url = f"{BASE_URL}/onboard"
    data = {
        "language": "Python",
        "learning_style": "Visual",
        "daily_hours": 2,
        "goal": "Get a job",
        "experience": "Beginner"
    }
    resp = requests.post(url, json=data)
    assert resp.status_code == 200
    body = resp.json()
    assert "user_id" in body
    return body["user_id"]

def test_onboard_endpoint(onboard_user):
    assert onboard_user is not None

def test_ask_endpoint():
    url = f"{BASE_URL}/ask"
    data = {
        "question": "Write a Python function to add two numbers.",
        "history": []
    }
    with requests.post(url, json=data, stream=True) as resp:
        assert resp.status_code == 200
        tokens = []
        for line in resp.iter_lines():
            if line:
                obj = json.loads(line)
                if "token" in obj:
                    tokens.append(obj["token"])
                elif obj.get("done"):
                    break
        assert len(tokens) > 0
        answer_text = "".join(tokens)
        assert "def" in answer_text  # crude check for function definition
