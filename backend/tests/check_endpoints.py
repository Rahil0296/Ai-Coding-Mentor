import requests

def check_endpoints():
    """Check which endpoints are available"""
    
    base_url = "http://localhost:8000"
    
    print("Checking available endpoints...")
    
    # Check OpenAPI docs
    try:
        response = requests.get(f"{base_url}/openapi.json")
        if response.status_code == 200:
            openapi = response.json()
            print("\nAvailable endpoints:")
            for path, methods in openapi.get("paths", {}).items():
                for method in methods:
                    print(f"  {method.upper()} {path}")
        else:
            print("Could not fetch OpenAPI spec")
    except Exception as e:
        print(f"Error checking endpoints: {e}")
    
    # Check specific endpoints
    endpoints_to_check = [
        ("GET", "/health"),
        ("POST", "/users/onboard"),
        ("POST", "/ask"),
        ("POST", "/ask/simple"),
        ("POST", "/execute"),
        ("POST", "/roadmaps"),
    ]
    
    print("\nTesting specific endpoints:")
    for method, endpoint in endpoints_to_check:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}")
            else:
                response = requests.options(f"{base_url}{endpoint}")
            
            if response.status_code in [200, 204, 405]:
                print(f"  ✓ {method} {endpoint} - Available")
            else:
                print(f"  ✗ {method} {endpoint} - Status {response.status_code}")
        except Exception as e:
            print(f"  ✗ {method} {endpoint} - Error: {e}")

if __name__ == "__main__":
    check_endpoints()