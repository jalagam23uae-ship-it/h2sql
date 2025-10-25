"""
Test simplified executequey -> graph workflow
Using just natural language (no SQL provided)
"""
import requests
import json

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

print("=" * 80)
print("TESTING: Simple executequey -> graph workflow (natural language only)")
print("=" * 80)

# Step 1: Execute query with natural language ONLY (no query field)
print("\nStep 1: Execute query with natural language")
print("-" * 80)

execute_payload = {
    "project_id": PROJECT_ID,
    "question": "how many customers are there?"
}

print(f"POST {BASE_URL}/executequey")
print(f"Payload: {json.dumps(execute_payload, indent=2)}")

try:
    response = requests.post(f"{BASE_URL}/executequey", json=execute_payload, timeout=30)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\n[OK] Query executed successfully!")
        print(f"Response keys: {list(result.keys())}")

        # Check for response_id
        if 'response_id' in result:
            response_id = result['response_id']
            print(f"\n[OK] Got response_id: {response_id}")

            # Display query results
            if 'rows' in result:
                print(f"\nQuery returned {len(result['rows'])} rows:")
                for i, row in enumerate(result['rows'][:5], 1):
                    print(f"  {i}. {row}")

            # Display LLM-generated SQL if available
            if 'llm_generated_sql' in result:
                print(f"\nLLM-generated SQL:\n{result['llm_generated_sql']}")

            print("\n[OK] WORKFLOW STEP 1 COMPLETE!")
            print(f"Response ID for graph endpoint: {response_id}")

        else:
            print("\n[FAIL] No response_id in executequey response!")
            print(f"Available keys: {list(result.keys())}")
            print(f"\nFull response: {json.dumps(result, indent=2)[:1000]}")

    else:
        print(f"\n[FAIL] Query execution failed!")
        error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
        print(f"Error: {error_text}")

except Exception as e:
    print(f"\n[ERROR] Exception occurred: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
