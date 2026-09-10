import os
import sys
import httpx
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def test_generate_summary():
    url = f"{BASE_URL}/api/generate-summary"
    payload = {
        "user_input": "Experienced software developer skilled in Python, FastAPI, and Cloud Architecture."
    }
    
    print("\n--- Testing /api/generate-summary ---")
    try:
        with httpx.Client(timeout=35.0) as client:
            response = client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            res = response.json()
            print("Response:", json.dumps(res, indent=2))
            
            assert response.status_code == 200
            assert res.get("status") == "success"
            assert "summary" in res and len(res["summary"]) > 0
            print("✅ Summary Test passed successfully!")
    except Exception as e:
        print("❌ Summary Test failed:", str(e))

def test_generate_section_bullets():
    url = f"{BASE_URL}/api/generate-section"
    payload = {
        "user_input": "Led office maintenance, negotiated vendor contracts, and reduced costs",
        "section_type": "experience_bullets",
        "job_title": "Facility Manager"
    }
    
    print("\n--- Testing /api/generate-section (bullets) ---")
    try:
        with httpx.Client(timeout=35.0) as client:
            response = client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            res = response.json()
            print("Response:", json.dumps(res, indent=2))
            
            assert response.status_code == 200
            assert res.get("status") == "success"
            assert "text" in res and "•" in res["text"]
            print("✅ Bullets Test passed successfully!")
    except Exception as e:
        print("❌ Bullets Test failed:", str(e))

def test_generate_section_skills():
    url = f"{BASE_URL}/api/generate-section"
    payload = {
        "user_input": "Marketing Manager",
        "section_type": "skills"
    }
    
    print("\n--- Testing /api/generate-section (skills) ---")
    try:
        with httpx.Client(timeout=35.0) as client:
            response = client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            res = response.json()
            print("Response:", json.dumps(res, indent=2))
            
            assert response.status_code == 200
            assert res.get("status") == "success"
            assert "text" in res and len(res["text"]) > 0
            print("✅ Skills Test passed successfully!")
    except Exception as e:
        print("❌ Skills Test failed:", str(e))

if __name__ == "__main__":
    print("Starting backend tests...")
    test_generate_summary()
    test_generate_section_bullets()
    test_generate_section_skills()