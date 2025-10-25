"""
Test Oracle database with simple query
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 23  # Oracle project

print("="*80)
print("TESTING ORACLE WITH OPENROUTER LLM")
print("="*80)
print(f"Project ID: {PROJECT_ID}")
print(f"Database: Oracle (TAQDB)")
print(f"Table: ECOM_SALES_A40CD89A")

# Test: Simple query
print("\n" + "="*80)
print("TEST: Total Sales by Product Category")
print("="*80)

query_payload = {
    "project_id": PROJECT_ID,
    "question": "show total_amount by product_category"
}

print(f"Query: {query_payload['question']}")

start = time.time()
response = requests.post(f"{BASE_URL}/executequey", json=query_payload, timeout=300)
elapsed = time.time() - start

print(f"\nStatus: {response.status_code}")
print(f"Time: {elapsed:.2f}s")

if response.status_code == 200:
    result = response.json()
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
    try:
        error = response.json()
        print(f"Error: {json.dumps(error, indent=2)}")
    except:
        print(f"Error: {response.text[:500]}")

print("\n" + "="*80)
