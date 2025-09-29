import asyncio
import json
import requests

async def test_agent_streaming():
    """Test the agent-powered ask endpoint."""
    
    # First, create a test user with unique email
    import time
    unique_email = f"test_{int(time.time())}@example.com"
    
    onboard_data = {
        "name": "Test User",
        "email": unique_email,
        "language": "en",
        "learning_style": "hands-on",
        "daily_hours": 2,
        "goal": "Learn Python basics",
        "experience": "beginner"
    }
    
    response = requests.post("http://localhost:8000/users/onboard", json=onboard_data)
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data["id"]
        print(f"Created user with ID: {user_id}")
    else:
        print("Failed to create user:", response.text)
        return
    
    # Test questions that should trigger different agent behaviors
    test_questions = [
        "How do I write a for loop in Python?",
        "Explain recursion with an example",
        "What's the difference between lists and tuples?",
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        ask_data = {
            "user_id": user_id,
            "question": question,
            "history": []
        }
        
        # Stream the response
        with requests.post(
            "http://localhost:8000/ask",
            json=ask_data,
            stream=True
        ) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            
                            if data.get("type") == "agent_action":
                                action = data.get("action")
                                content = data.get("content", "")
                                
                                if action == "think":
                                    print(f"\n🤔 THINKING: {content[:100]}...")
                                elif action == "explain":
                                    print(f"\n📚 EXPLANATION: {content}")
                                elif action == "code":
                                    print(f"\n💻 CODE EXAMPLE:")
                                    print(content)
                                elif action == "execute":
                                    print(f"\n▶️ EXECUTING CODE:")
                                    print(content)
                                elif action == "quiz":
                                    print(f"\n❓ QUIZ: {content}")
                                elif action == "suggest":
                                    print(f"\n💡 SUGGESTION: {content}")
                            
                            elif data.get("type") == "partial":
                                # Partial content, could show loading indicator
                                pass
                            
                            elif data.get("type") == "done":
                                print("\n✅ Response complete")
                        except json.JSONDecodeError:
                            print(f"Failed to parse: {line}")
            else:
                print(f"Error: {response.status_code} - {response.text}")


async def test_code_execution():
    """Test the code execution endpoint."""
    print("\n" + "="*60)
    print("Testing Code Execution")
    print("="*60)
    
    # First create a user for testing
    import time
    unique_email = f"exec_test_{int(time.time())}@example.com"
    
    onboard_data = {
        "name": "Exec Test User",
        "email": unique_email,
        "language": "en",
        "learning_style": "hands-on",
        "daily_hours": 2,
        "goal": "Test execution",
        "experience": "beginner"
    }
    
    response = requests.post("http://localhost:8000/users/onboard", json=onboard_data)
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data["id"]
        print(f"Created test user with ID: {user_id}")
    else:
        print("Failed to create user for execution test")
        return
    
    # Test Python execution
    execute_data = {
        "user_id": user_id,
        "code": """
# Calculate factorial
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(f"Factorial of 5 is: {factorial(5)}")
print("Hello from executed Python code!")
""",
        "language": "python"
    }
    
    response = requests.post("http://localhost:8000/execute", json=execute_data)
    if response.status_code == 200:
        result = response.json()
        print(f"\nExecution Status: {result['status']}")
        if result.get('output'):
            print(f"Output:\n{result['output']}")
        if result.get('error'):
            print(f"Error:\n{result['error']}")
    else:
        print(f"Execution failed: {response.text}")


if __name__ == "__main__":
    print("Testing Agentic AI Coding Mentor...")
    
    # Run tests
    asyncio.run(test_agent_streaming())
    asyncio.run(test_code_execution())