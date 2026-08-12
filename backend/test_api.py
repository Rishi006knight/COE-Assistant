import urllib.request
import json
import sys

def run_test():
    url = 'http://127.0.0.1:8000/api/query'
    payload = {
        'course_code': None,
        'portion_query': 'repeated questions in Computer Vision'
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print(f"Sending POST request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        # 60 second timeout
        with urllib.request.urlopen(req, timeout=60) as response:
            status_code = response.getcode()
            response_data = response.read().decode('utf-8')
            print(f"\nResponse Status: {status_code}")
            print("First 500 characters of response:")
            print("-" * 50)
            print(response_data[:500])
            print("-" * 50)
            if len(response_data) > 500:
                print(f"... (total length: {len(response_data)} characters)")
            return True
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Error details: {error_body}")
        except Exception:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"\nConnection Error: {e.reason}")
        print("Please check if the backend server is running and listening on port 8000.")
        return False
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
