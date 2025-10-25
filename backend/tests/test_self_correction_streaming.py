# test_self_correction_streaming.py
import requests
import json

url = "http://localhost:8000/ask"
payload = {
    "user_id": 1,
    "question": "Write a function to find the factorial of a number using recursion",
    "history": []
}

print("🚀 Testing Self-Correction Loop with Streaming...\n")

response = requests.post(url, json=payload, stream=True)

print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    full_response = ""
    metrics = None
    
    for line in response.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                msg_type = data.get("type")
                
                if msg_type == "learning_analysis":
                    print(f"📊 {data['message']}")
                elif msg_type == "reasoning":
                    print(f"🤔 Reasoning: {data['content']}")
                elif msg_type == "response":
                    full_response += data.get("content", "")
                elif msg_type == "complete":
                    metrics = data.get("metrics", {})
                    print(f"\n✅ Complete!")
                    print(f"   Confidence: {metrics.get('confidence')}%")
                    print(f"   Execution Time: {metrics.get('execution_time_ms')}ms")
                    print(f"   Learning Active: {metrics.get('learning_active')}")
                elif msg_type == "error":
                    print(f"❌ Error: {data['message']}")
            except json.JSONDecodeError:
                pass
    
    print(f"\n📝 Full Response:\n{full_response[:500]}...")  # First 500 chars
    
    if metrics:
        print(f"\n📊 Final Metrics:")
        print(f"   - Confidence: {metrics.get('confidence')}%")
        print(f"   - Execution Time: {metrics.get('execution_time_ms')}ms")

else:
    print(f"❌ Error {response.status_code}")
    print(response.text)
