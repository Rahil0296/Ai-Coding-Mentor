import requests
import json
import time

def test_agent_endpoint():
    """Test the learning agent endpoint (/ask) vs simple endpoint"""
    
    # Create a test user
    print("Creating test user...")
    unique_email = f"agent_test_{int(time.time())}@example.com"
    
    user_response = requests.post(
        "http://localhost:8000/users/onboard",
        json={
            "name": "Agent Test User",
            "email": unique_email,
            "programming_language": "Python",
            "learning_style": "hands-on",
            "daily_hours": 2,
            "goal": "Master Python",
            "experience": "beginner"
        }
    )
    
    if user_response.status_code != 200:
        print(f"Failed to create user: {user_response.text}")
        return
    
    user_id = user_response.json()["id"]
    print(f"✓ Created user ID: {user_id}\n")
    
    # Test question
    question = "What is a Python function?"
    
    print("="*60)
    print("TESTING AGENT ENDPOINT (/ask)")
    print("="*60)
    
    response = requests.post(
        "http://localhost:8000/ask",
        json={
            "user_id": user_id,
            "question": question,
            "history": []
        },
        stream=True
    )
    
    if response.status_code == 200:
        print("\nStreaming response:\n")
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    
                    # Show each phase of the agent's response
                    if data.get("type") == "learning_analysis":
                        print(f"🧠 LEARNING: {data['message']}")
                        print(f"   Session ID: {data['session_id']}\n")
                    
                    elif data.get("type") == "reasoning":
                        print(f"🤔 REASONING: {data['content']}")
                        print(f"   Improvement Active: {data['improvement_active']}\n")
                    
                    elif data.get("type") == "response":
                        print(data['content'], end='', flush=True)
                    
                    elif data.get("type") == "complete":
                        metrics = data.get("metrics", {})
                        print(f"\n\n✅ COMPLETE")
                        print(f"   Confidence: {metrics.get('confidence')}%")
                        print(f"   Time: {metrics.get('execution_time_ms')}ms")
                        print(f"   Learning Active: {metrics.get('learning_active')}")
                        print(f"   Session: {metrics.get('session_id')}")
                    
                    elif data.get("type") == "error":
                        print(f"\n❌ ERROR: {data['message']}")
                        print(f"   Error ID: {data['error_id']}")
                
                except json.JSONDecodeError as e:
                    print(f"Failed to parse: {line}")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
    
    # Now check performance metrics
    print("\n" + "="*60)
    print("CHECKING PERFORMANCE METRICS")
    print("="*60)
    
    metrics_response = requests.get(f"http://localhost:8000/ask/performance/{user_id}")
    if metrics_response.status_code == 200:
        metrics = metrics_response.json()
        print(json.dumps(metrics, indent=2))
    else:
        print(f"Failed to get metrics: {metrics_response.text}")

if __name__ == "__main__":
    test_agent_endpoint()