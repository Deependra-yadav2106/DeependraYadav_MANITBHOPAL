import requests
import json
import time
import os

def test_multiple_files():
    base_url = "http://localhost:8000/extract-bill-data"
    file_server_url = "http://localhost:8081/TRAINING_SAMPLES"
    
    # List files in the directory
    sample_dir = os.path.join("sample_data", "TRAINING_SAMPLES")
    if not os.path.exists(sample_dir):
        print(f"Directory not found: {sample_dir}")
        return

    files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
    files.sort()
    
    print(f"Found {len(files)} files to test.")
    
    results = {}
    
    for filename in files:
        print(f"\nTesting {filename}...")
        doc_url = f"{file_server_url}/{filename}"
        payload = {"document": doc_url}
        
        try:
            start_time = time.time()
            response = requests.post(base_url, json=payload)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("is_success"):
                    print(f"  [FAIL] API Error: {data.get('message')}")
                    results[filename] = {"status": "Failed", "error": data.get("message")}
                    continue

                items = []
                total_amount = 0
                
                extracted_data = data.get("data")
                if extracted_data and extracted_data.get("pagewise_line_items"):
                    for page in extracted_data["pagewise_line_items"]:
                        for item in page["bill_items"]:
                            items.append(item["item_name"])
                            total_amount += item["item_amount"] if item["item_amount"] else 0
                
                item_count = extracted_data.get("total_item_count", 0) if extracted_data else 0
                
                print(f"  [PASS] {duration:.2f}s | Items: {item_count} | Total: {total_amount:.2f}")
                
                results[filename] = {
                    "status": "Success",
                    "duration": round(duration, 2),
                    "item_count": item_count,
                    "calculated_total": round(total_amount, 2),
                    "first_3_items": items[:3]
                }
            else:
                print(f"  [FAIL] Status: {response.status_code}")
                results[filename] = {"status": f"Failed: {response.status_code}", "error": response.text}
        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            results[filename] = {"status": "Error", "message": str(e)}
            
    print("\n=== Test Results Summary ===")
    print(json.dumps(results, indent=2))
    
    # Save results to file for analysis
    with open("bulk_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_multiple_files()
