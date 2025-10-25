"""
Simple single query test to verify API key works
"""
import requests
import json

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 23  # Oracle

print("=" * 80)
print("SIMPLE QUERY TEST")
print("=" * 80)

response = requests.post(
    f"{BASE_URL}/executequey",
    json={"project_id": PROJECT_ID, "question": "How many orders are there?"},
    timeout=60
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"\n[SUCCESS]")
    print(f"SQL: {data.get('llm_generated_sql', '')}")
    print(f"Result: {data.get('db_result', [])}")
else:
    print(f"\n[FAIL]")
    print(f"Response: {response.text[:300]}")

print("=" * 80)
