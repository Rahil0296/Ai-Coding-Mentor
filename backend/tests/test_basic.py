import requests
import json
import time

def test_basic():
    """Test basic functionality without streaming"""
    
    # 1. Test health
    print("1. Testing health endpoint...")
    response = requests.get("http://localhost:8000/health")
    print(f"   Health: {response.status_code} - {response.json() if response.status_code == 200 else response.text}")
    
    # 2. Create user
    print("\n2. Creating user...")
    unique_email = f"basic_test_{int(time.time())}@example.com"
    user_data = {
        "name": "Basic Test",
        "email": unique_email,
        "language": "en",
        "learning_style": "visual",
        "daily_hours": 1,
        "goal": "Test basics",
        "experience": "beginner"
    }
    
    response = requests.post("http://localhost:8000/users/onboard", json=user_data)
    if response.status_code == 200:
        user_info = response.json()
        user_id = user_info["id"]
        print(f"   Created user ID: {user_id}")
    else:
        print(f"   Failed: {response.status_code} - {response.text}")
        return
    
    # 3. Test ask endpoint (no streaming, collect full response)
    print("\n3. Testing /ask endpoint (collecting chunks)...")
    ask_data = {
        "user_id": user_id,
        "question": "What is a variable in Python?",
        "history": []
    }
    
    try:
        # Don't use stream=True, just get the streaming response normally
        response = requests.post("http://localhost:8000/ask", json=ask_data, stream=True)
        
        if response.status_code == 200:
            chunks = []
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    chunks.append(chunk)
                    print(".", end="", flush=True)
            
            print(f"\n   Received {len(chunks)} chunks")
            
            # Try to parse the chunks
            full_response = "".join(chunks)
            lines = full_response.strip().split("\n")
            print(f"   Total lines: {len(lines)}")
            
            # Show first few lines
            for i, line in enumerate(lines[:3]):
                try:
                    data = json.loads(line)
                    print(f"   Line {i}: {list(data.keys())}")
                except:
                    print(f"   Line {i}: Could not parse - {line[:50]}...")
        else:
            print(f"   Failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {e}")
    
    # 4. Check if /ask/simple exists
    print("\n4. Checking /ask/simple endpoint...")
    response = requests.post("http://localhost:8000/ask/simple", json=ask_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print("   /ask/simple endpoint not found - using /ask instead")

if __name__ == "__main__":
    test_basic()