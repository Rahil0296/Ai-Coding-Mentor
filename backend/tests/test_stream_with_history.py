import requests
import json

url = "http://127.0.0.1:8000/ask"
data = {
    "question": "How do I write a Python decorator?",
    "history": [
        {"user": "What is a Python function?", "assistant": "A function is a block of code that performs a specific task and can be reused."},
        {"user": "How do I define a function?", "assistant": "You define a function in Python using the def keyword followed by the function name and parentheses."}
    ]
}

with requests.post(url, json=data, stream=True) as resp:
    for line in resp.iter_lines():
        if line:
            obj = json.loads(line)
            if "token" in obj:
                print(obj["token"], end="", flush=True)
            elif obj.get("done"):
                print("\n[STREAM COMPLETE]")