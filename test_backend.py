import urllib.request
import json
import time

def test_generate_summary():
    url = "http://127.0.0.1:8000/api/generate-summary"
    payload = {
        "user_input": "My name is Rufus. I love capturing images."
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print("Summary Response:", res)
            assert "summary" in res
            assert res.get("status") == "success"
            assert len(res["summary"]) > 0
            print("Summary Test passed successfully!")
    except urllib.error.HTTPError as e:
        print("HTTP Error (Summary):", e.code)
        print("Response body:", e.read().decode("utf-8"))
    except Exception as e:
        print("Summary Test failed:", str(e))

def test_generate_section_bullets():
    url = "http://127.0.0.1:8000/api/generate-section"
    payload = {
        "user_input": "Led office maintenance, negotiated vendor contracts, and reduced costs",
        "section_type": "experience_bullets",
        "job_title": "Facility Manager"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print("Bullets Response:", res)
            assert "text" in res
            assert res.get("status") == "success"
            assert "•" in res["text"]
            print("Bullets Test passed successfully!")
    except urllib.error.HTTPError as e:
        print("HTTP Error (Bullets):", e.code)
        print("Response body:", e.read().decode("utf-8"))
    except Exception as e:
        print("Bullets Test failed:", str(e))

def test_generate_section_skills():
    url = "http://127.0.0.1:8000/api/generate-section"
    payload = {
        "user_input": "Marketing Manager",
        "section_type": "skills"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            print("Skills Response:", res)
            assert "text" in res
            assert res.get("status") == "success"
            assert len(res["text"]) > 0
            print("Skills Test passed successfully!")
    except urllib.error.HTTPError as e:
        print("HTTP Error (Skills):", e.code)
        print("Response body:", e.read().decode("utf-8"))
    except Exception as e:
        print("Skills Test failed:", str(e))

if __name__ == "__main__":
    print("Starting backend tests...")
    test_generate_summary()
    test_generate_section_bullets()
    test_generate_section_skills()
