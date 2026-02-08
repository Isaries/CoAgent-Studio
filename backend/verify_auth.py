import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_auth():
    print("Testing /login/test-token without cookies...")
    try:
        # We need to hit the backend directly. 
        # The user has `target: 'http://backend:8000'` in vite config, so backend is likely running on 8000.
        # But wait, looking at user's files, it seems they might be running locally.
        # Let's try localhost:8000.
        response = requests.post(f"{BASE_URL}/login/test-token")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200 and (response.text == "null" or response.json() is None):
            print("SUCCESS: Endpoint returned 200 OK and null for unauthenticated request.")
        elif response.status_code == 401:
            print("FAILURE: Endpoint still returned 401 Unauthorized.")
        else:
            print(f"UNEXPECTED: {response.status_code}")

    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    test_auth()
