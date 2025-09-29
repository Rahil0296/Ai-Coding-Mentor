import requests
import json

# Simple test to see raw model output
def test_simple():
    # Use existing user or create new one
    user_id = 1  # Adjust if needed
    
    ask_data = {
        "user_id": user_id,
        "question": "What is a Python list?",
        "history": []
    }
    
    print("Sending question:", ask_data["question"])
    print("-" * 60)
    
    # Use the simple endpoint first to see raw output
    with requests.post(
        "http://localhost:8000/ask/simple",
        json=ask_data,
        stream=True
    ) as response:
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "token" in data:
                            full_response += data["token"]
                            print(data["token"], end="", flush=True)
                    except:
                        pass
            print("\n" + "-" * 60)
            print("Full response received")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    test_simple()