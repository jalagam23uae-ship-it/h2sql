"""
Test Oracle database connection and upload e-commerce data
"""
import requests
import json

BASE_URL = "http://localhost:11901/h2s/db/projects"

# Create new project with Oracle connection
print("="*80)
print("CREATING ORACLE PROJECT")
print("="*80)

oracle_project = {
    "name": "oracle_ecommerce_test",
    "train_id": "oracle_train_001",
    "db_type": "oracle",
    "con_string": "192.168.1.101:1521",
    "database": "TAQDB",  # SID
    "username": "TESTDB_USER",
    "password": "TESTDB_USER",
    "db_metadata": []
}

print("Creating Oracle project...")
print(f"Connection: oracle://{oracle_project['username']}@{oracle_project['con_string']}/{oracle_project['database']}")

response = requests.post(BASE_URL, json=oracle_project, timeout=30)

print(f"\nStatus: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    project_data = response.json()
    project_id = project_data['id']

    print(f"\n[OK] Oracle project created successfully!")
    print(f"Project ID: {project_id}")

    # Now upload e-commerce data to Oracle
    print("\n" + "="*80)
    print("UPLOADING E-COMMERCE DATA TO ORACLE")
    print("="*80)

    file_path = "D:\\testing-files\\ecom_sales.csv"
    upload_url = "http://localhost:11901/h2s/data-upload/upload"

    with open(file_path, 'rb') as f:
        files = {'file': ('ecom_sales.csv', f, 'text/csv')}
        data = {'project_id': project_id}

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

            query_url = "http://localhost:11901/h2s/data-upload/executequey"
            query_payload = {
                "project_id": project_id,
                "question": "what is the total sales amount for each product category?"
            }

            print(f"Query: {query_payload['question']}")

            import time
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
else:
    print(f"\n[FAIL] Project creation failed!")
    print(f"Error: {response.text}")

print("\n" + "="*80)
