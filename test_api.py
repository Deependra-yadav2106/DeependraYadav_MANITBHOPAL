import requests
import json

def test_api():
    url = "http://localhost:8000/extract-bill-data"
    payload = {
        "document": "http://localhost:8081/TRAINING_SAMPLES/train_sample_1.pdf" 
        # Note: Using one of the URLs from the problem description or postman collection if available. 
        # The one above is from the problem description example.
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api()
