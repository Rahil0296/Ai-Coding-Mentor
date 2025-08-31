import requests

resp = requests.get("http://127.0.0.1:8000/health")
print(resp.json())
