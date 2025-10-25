"""
Test OpenRouter API integration with H2SQL
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22  # PostgreSQL project

print("="*80)
print("TESTING OPENROUTER LLM WITH POSTGRESQL")
print("="*80)
print(f"Project ID: {PROJECT_ID}")
print(f"LLM: OpenRouter API (meta-llama/llama-3.2-3b-instruct:free)")

# Test 1: Simple count query
print("\n" + "="*80)
print("TEST 1: Simple Count Query")
print("="*80)

query1_payload = {
    "project_id": PROJECT_ID,
    "question": "how many customers are there?"
}

print(f"Query: {query1_payload['question']}")

start = time.time()
response1 = requests.post(f"{BASE_URL}/executequey", json=query1_payload, timeout=300)
elapsed1 = time.time() - start

print(f"\nStatus: {response1.status_code}")
print(f"Time: {elapsed1:.2f}s")

if response1.status_code == 200:
    result1 = response1.json()
    print(f"\n[OK] Query executed successfully!")

    if 'llm_generated_sql' in result1:
        print(f"\nLLM-generated SQL:")
        print(result1['llm_generated_sql'])

    if 'db_result' in result1:
        print(f"\nResults ({len(result1['db_result'])} rows):")
        for row in result1['db_result'][:5]:
            print(f"  {row}")
else:
    print(f"\n[FAIL] Query failed!")
    print(f"Error: {response1.text}")

# Test 2: Group by query
print("\n" + "="*80)
print("TEST 2: Group By Query")
print("="*80)

query2_payload = {
    "project_id": PROJECT_ID,
    "question": "count customers by segment"
}

print(f"Query: {query2_payload['question']}")

start = time.time()
response2 = requests.post(f"{BASE_URL}/executequey", json=query2_payload, timeout=300)
elapsed2 = time.time() - start

print(f"\nStatus: {response2.status_code}")
print(f"Time: {elapsed2:.2f}s")

if response2.status_code == 200:
    result2 = response2.json()
    print(f"\n[OK] Query executed successfully!")

    if 'llm_generated_sql' in result2:
        print(f"\nLLM-generated SQL:")
        print(result2['llm_generated_sql'])

    if 'db_result' in result2:
        print(f"\nResults ({len(result2['db_result'])} rows):")
        for row in result2['db_result'][:10]:
            print(f"  {row}")
else:
    print(f"\n[FAIL] Query failed!")
    print(f"Error: {response2.text}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Test 1: {'PASS' if response1.status_code == 200 else 'FAIL'} ({elapsed1:.2f}s)")
print(f"Test 2: {'PASS' if response2.status_code == 200 else 'FAIL'} ({elapsed2:.2f}s)")
print("="*80)
