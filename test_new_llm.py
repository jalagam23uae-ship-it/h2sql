"""
Test new LLM configuration: http://192.168.1.6:3034/v1/chat/completions
Model: Llama-4-Scout-17B-16E-Instruct
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

print("=" * 80)
print("TESTING: New LLM Configuration")
print("LLM URL: http://192.168.1.6:3034/v1")
print("Model: Llama-4-Scout-17B-16E-Instruct")
print("=" * 80)

# Test 1: Simple count query
print("\nTest 1: Simple count query")
print("-" * 80)

test_payload = {
    "project_id": PROJECT_ID,
    "question": "how many customers are there?"
}

print(f"POST {BASE_URL}/executequey")
print(f"Payload: {json.dumps(test_payload, indent=2)}")

start_time = time.time()

try:
    response = requests.post(f"{BASE_URL}/executequey", json=test_payload, timeout=90)
    elapsed = time.time() - start_time

    print(f"\nStatus: {response.status_code}")
    print(f"Response time: {elapsed:.2f}s")

    if response.status_code == 200:
        result = response.json()
        print("\n[OK] LLM responded successfully!")

        if 'llm_generated_sql' in result:
            print(f"\nLLM-generated SQL:\n{result['llm_generated_sql']}")

        if 'response_id' in result:
            print(f"\nResponse ID: {result['response_id']}")

        if 'db_result' in result:
            print(f"Query returned {len(result['db_result'])} rows")

        print("\n[SUCCESS] New LLM configuration is working!")

    else:
        print(f"\n[FAIL] Request failed!")
        print(f"Error: {response.text[:500]}")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n[ERROR] Exception occurred after {elapsed:.2f}s")
    print(f"Error: {str(e)}")

# Test 2: Complex query with GROUP BY
print("\n" + "=" * 80)
print("\nTest 2: Complex query with GROUP BY")
print("-" * 80)

test_payload2 = {
    "project_id": PROJECT_ID,
    "question": "count customers by segment"
}

print(f"POST {BASE_URL}/executequey")
print(f"Payload: {json.dumps(test_payload2, indent=2)}")

start_time = time.time()

try:
    response = requests.post(f"{BASE_URL}/executequey", json=test_payload2, timeout=90)
    elapsed = time.time() - start_time

    print(f"\nStatus: {response.status_code}")
    print(f"Response time: {elapsed:.2f}s")

    if response.status_code == 200:
        result = response.json()
        print("\n[OK] LLM responded successfully!")

        if 'llm_generated_sql' in result:
            print(f"\nLLM-generated SQL:\n{result['llm_generated_sql']}")

        if 'db_result' in result:
            print(f"\nQuery returned {len(result['db_result'])} rows")
            if len(result['db_result']) > 0:
                print("Sample results:")
                for i, row in enumerate(result['db_result'][:5], 1):
                    print(f"  {i}. {row}")

        print("\n[SUCCESS] Complex query working!")

    else:
        print(f"\n[FAIL] Request failed!")
        print(f"Error: {response.text[:500]}")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n[ERROR] Exception occurred after {elapsed:.2f}s")
    print(f"Error: {str(e)}")

print("\n" + "=" * 80)
print("LLM TEST COMPLETE")
print("=" * 80)
