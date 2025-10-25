"""
Test Oracle database with existing project ID 23
"""
import requests
import json
import time

PROJECT_ID = 23  # Existing Oracle project
BASE_URL = "http://localhost:11901/h2s/data-upload"

print("="*80)
print("UPLOADING E-COMMERCE DATA TO ORACLE")
print("="*80)
print(f"Project ID: {PROJECT_ID}")

file_path = "D:\\testing-files\\ecom_sales.csv"
upload_url = f"{BASE_URL}/upload"

with open(file_path, 'rb') as f:
    files = {'file': ('ecom_sales.csv', f, 'text/csv')}
    data = {'project_id': PROJECT_ID}

    print(f"Uploading {file_path} to Oracle...")
    upload_response = requests.post(upload_url, files=files, data=data, timeout=300)

    print(f"\nStatus: {upload_response.status_code}")
    print(f"Response: {json.dumps(upload_response.json(), indent=2)}")

    if upload_response.status_code == 200:
        result = upload_response.json()
        table_name = result.get('tableName')
        rows = result.get('rowsInserted')

        print(f"\n[OK] Data uploaded successfully!")
        print(f"Table: {table_name}")
        print(f"Rows: {rows}")

        # Test query on Oracle data
        print("\n" + "="*80)
        print("TESTING QUERY ON ORACLE DATA")
        print("="*80)

        query_url = f"{BASE_URL}/executequey"
        query_payload = {
            "project_id": PROJECT_ID,
            "question": "what is the total sales amount for each product category?"
        }

        print(f"Query: {query_payload['question']}")

        start = time.time()
        query_response = requests.post(query_url, json=query_payload, timeout=300)
        elapsed = time.time() - start

        print(f"\nStatus: {query_response.status_code}")
        print(f"Time: {elapsed:.2f}s")

        if query_response.status_code == 200:
            result = query_response.json()
            print(f"\n[OK] Query executed successfully!")

            if 'llm_generated_sql' in result:
                print(f"\nLLM-generated SQL:")
                print(result['llm_generated_sql'])

            if 'db_result' in result:
                print(f"\nResults ({len(result['db_result'])} rows):")
                for row in result['db_result'][:10]:
                    print(f"  {row}")
        else:
            print(f"\n[FAIL] Query failed!")
            print(f"Error: {query_response.text}")
    else:
        print(f"\n[FAIL] Upload failed!")
        print(f"Error: {upload_response.text}")

print("\n" + "="*80)
