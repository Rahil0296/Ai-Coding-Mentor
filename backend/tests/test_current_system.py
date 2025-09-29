import requests
import json
import time

def test_current_system():
    """Test the system as it currently works"""
    
    # Step 1: Create a new user
    print("1. Creating a new user...")
    unique_email = f"test_{int(time.time())}@example.com"
    
    onboard_response = requests.post(
        "http://localhost:8000/users/onboard",
        json={
            "name": "Current Test User",
            "email": unique_email,
            "language": "en",
            "learning_style": "hands-on",
            "daily_hours": 2,
            "goal": "Learn Python basics",
            "experience": "beginner"
        }
    )
    
    if onboard_response.status_code == 200:
        user_data = onboard_response.json()
        user_id = user_data["id"]
        print(f"✓ User created with ID: {user_id}")
        print(f"  Profile: {user_data['profile']['learning_style']} learner, {user_data['profile']['experience']} level")
    else:
        print(f"✗ Failed to create user: {onboard_response.text}")
        return
    
    # Step 2: Ask a question using the simple endpoint
    print("\n2. Testing simple ask endpoint...")
    questions = [
        "What is a Python list?",
        "How do I use a for loop?",
        "Explain functions in Python"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n   Question {i}: {question}")
        print("   " + "-" * 50)
        
        response = requests.post(
            "http://localhost:8000/ask/simple",
            json={
                "user_id": user_id,
                "question": question,
                "history": []
            },
            stream=True
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "token" in data:
                            full_response += data["token"]
                    except:
                        pass
            
            # Show first 200 chars of response
            preview = full_response[:200] + "..." if len(full_response) > 200 else full_response
            print(f"   Response preview: {preview}")
            print(f"   ✓ Full response length: {len(full_response)} characters")
        else:
            print(f"   ✗ Error: {response.status_code}")
    
    # Step 3: Test creating a roadmap
    print("\n3. Creating a learning roadmap...")
    roadmap_response = requests.post(
        "http://localhost:8000/roadmaps",
        json={
            "user_id": user_id,
            "roadmap_json": {
                "title": "Python Basics Learning Path",
                "duration": "4 weeks",
                "topics": [
                    {"week": 1, "topic": "Variables and Data Types"},
                    {"week": 2, "topic": "Control Flow (if, loops)"},
                    {"week": 3, "topic": "Functions and Modules"},
                    {"week": 4, "topic": "Lists and Dictionaries"}
                ]
            }
        }
    )
    
    if roadmap_response.status_code == 200:
        roadmap_data = roadmap_response.json()
        print(f"✓ Roadmap created with ID: {roadmap_data['id']}")
    else:
        print(f"✗ Failed to create roadmap: {roadmap_response.text}")
    
    # Step 4: Ask a question with roadmap context
    print("\n4. Testing ask with roadmap context...")
    response = requests.post(
        "http://localhost:8000/ask/simple",
        json={
            "user_id": user_id,
            "question": "What should I learn next based on my roadmap?",
            "history": []
        },
        stream=True
    )
    
    if response.status_code == 200:
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "token" in data:
                        full_response += data["token"]
                except:
                    pass
        
        preview = full_response[:300] + "..." if len(full_response) > 300 else full_response
        print(f"   Response: {preview}")
    
    # Step 5: Test health check
    print("\n5. Testing health check...")
    health_response = requests.get("http://localhost:8000/health")
    if health_response.status_code == 200:
        print(f"✓ Health check: {health_response.json()}")
    
    print("\n✅ All basic tests completed!")


if __name__ == "__main__":
    test_current_system()