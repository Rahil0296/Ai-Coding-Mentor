import requests
import json

def test_ask_endpoint():
    url = "http://127.0.0.1:8000/ask"
    data = {"question": "Tell me 50 words about python language"}
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