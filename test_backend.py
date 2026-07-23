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
            print("Response:", res)
            assert "summary" in res
            assert res.get("status") == "success"
            assert len(res["summary"]) > 0
            print("Test passed successfully!")
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code)
        print("Response body:", e.read().decode("utf-8"))
    except Exception as e:
        print("Test failed:", str(e))

if __name__ == "__main__":
    # Wait a bit for the server to be up
    time.sleep(2)
    test_generate_summary()
