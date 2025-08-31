import requests
import json

url = "http://127.0.0.1:8000/ask"
data = {"question": "Tell me 50 words about python language"}

with requests.post(url, json=data, stream=True) as resp:
    for line in resp.iter_lines():
        if line:
            obj = json.loads(line)
            if "token" in obj:
                print(obj["token"], end="", flush=True)
            elif obj.get("done"):
                print("\n[STREAM COMPLETE]")
