"""
Test Llama-4-Scout model via OpenRouter
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"

print("="*80)
print("TESTING LLAMA-4-SCOUT VIA OPENROUTER")
print("="*80)
print("Model: meta-llama/llama-4-scout")
print("Provider: OpenRouter API")

# Test 1: PostgreSQL
print("\n" + "="*80)
print("TEST 1: POSTGRESQL - Simple Count")
print("="*80)

query1 = {
    "project_id": 22,
    "question": "how many customers are there?"
}

print(f"Query: {query1['question']}")
start = time.time()
resp1 = requests.post(f"{BASE_URL}/executequey", json=query1, timeout=300)
elapsed1 = time.time() - start

print(f"Status: {resp1.status_code} ({elapsed1:.2f}s)")
if resp1.status_code == 200:
    result1 = resp1.json()
    print(f"[OK] SQL: {result1.get('llm_generated_sql', 'N/A')}")
    print(f"Result: {result1.get('db_result', [])[0] if result1.get('db_result') else 'N/A'}")
else:
    print(f"[FAIL] {resp1.text[:200]}")

# Test 2: PostgreSQL Group By
print("\n" + "="*80)
print("TEST 2: POSTGRESQL - Group By")
print("="*80)

query2 = {
    "project_id": 22,
    "question": "show me sales total by product category"
}

print(f"Query: {query2['question']}")
start = time.time()
resp2 = requests.post(f"{BASE_URL}/executequey", json=query2, timeout=300)
elapsed2 = time.time() - start

print(f"Status: {resp2.status_code} ({elapsed2:.2f}s)")
if resp2.status_code == 200:
    result2 = resp2.json()
    print(f"[OK] SQL: {result2.get('llm_generated_sql', 'N/A')}")
    db_results = result2.get('db_result', [])
    print(f"Rows returned: {len(db_results)}")
    for row in db_results[:5]:
        print(f"  {row}")
else:
    print(f"[FAIL] {resp2.text[:200]}")

# Test 3: Oracle
print("\n" + "="*80)
print("TEST 3: ORACLE - Sum by Category")
print("="*80)

query3 = {
    "project_id": 23,
    "question": "what is the sum of total_amount grouped by product_category?"
}

print(f"Query: {query3['question']}")
start = time.time()
resp3 = requests.post(f"{BASE_URL}/executequey", json=query3, timeout=300)
elapsed3 = time.time() - start

print(f"Status: {resp3.status_code} ({elapsed3:.2f}s)")
if resp3.status_code == 200:
    result3 = resp3.json()
    print(f"[OK] SQL: {result3.get('llm_generated_sql', 'N/A')}")
    db_results = result3.get('db_result', [])
    print(f"Rows returned: {len(db_results)}")
    for row in db_results[:10]:
        print(f"  {row}")
else:
    print(f"[FAIL] Error:")
    try:
        error = resp3.json()
        print(f"  {error.get('detail', resp3.text)[:300]}")
    except:
        print(f"  {resp3.text[:300]}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"PostgreSQL Test 1: {'PASS' if resp1.status_code == 200 else 'FAIL'} ({elapsed1:.2f}s)")
print(f"PostgreSQL Test 2: {'PASS' if resp2.status_code == 200 else 'FAIL'} ({elapsed2:.2f}s)")
print(f"Oracle Test 3:     {'PASS' if resp3.status_code == 200 else 'FAIL'} ({elapsed3:.2f}s)")
print("="*80)
