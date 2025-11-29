import requests
import json

def test_hosted_api():
    url = "https://project-api-kcnf.onrender.com/extract-bill-data"
    # Use the public URL found in the postman collection
    document_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
    
    payload = {"document": document_url}
    
    print(f"Testing API at: {url}")
    print(f"Document: {document_url}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Success! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("Failed. Response Text:")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_hosted_api()
