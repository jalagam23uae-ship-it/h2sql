"""
Test Query on Uploaded Data

Verifies that uploaded tables can be queried successfully
"""
import requests
import json

url = "http://localhost:11901/h2s/data-upload/executequey"
project_id = 22

# Test queries for uploaded tables
test_queries = [
    {
        "name": "List all uploaded tables",
        "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND (table_name LIKE 'CUSTOMERS%' OR table_name LIKE 'CUSTOMERROLE%' OR table_name LIKE 'EMPLOYEES%') ORDER BY table_name",
        "question": "What tables have been uploaded?"
    },
    {
        "name": "Count CUSTOMERS rows",
        "query": "SELECT COUNT(*) as total_customers FROM CUSTOMERS_59C96545",
        "question": "How many customers are there?"
    },
    {
        "name": "Count CUSTOMERROLE rows",
        "query": "SELECT COUNT(*) as total_roles FROM CUSTOMERROLE_2857A605",
        "question": "How many customer roles are there?"
    },
    {
        "name": "Count EMPLOYEES rows",
        "query": "SELECT COUNT(*) as total_employees FROM EMPLOYEES_WITH_NORMAL_HEADINGS_07A68017",
        "question": "How many employees are there?"
    },
    {
        "name": "Sample CUSTOMERS data",
        "query": "SELECT * FROM CUSTOMERS_59C96545 LIMIT 3",
        "question": "Show me sample customer data"
    }
]

print("=" * 80)
print("QUERY TEST ON UPLOADED DATA")
print("=" * 80)
print(f"Endpoint: {url}")
print(f"Project ID: {project_id}\n")

success_count = 0
failed_count = 0

for test in test_queries:
    print(f"\n{'=' * 80}")
    print(f"Test: {test['name']}")
    print(f"{'=' * 80}")
    print(f"Query: {test['query'][:100]}...")

    try:
        payload = {
            "project_id": project_id,
            "question": test["question"],
            "query": test["query"]
        }

        response = requests.post(url, json=payload, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS!")

            # Display result based on structure
            if isinstance(result, dict):
                if 'rows' in result:
                    print(f"  Rows returned: {len(result['rows'])}")
                    if len(result['rows']) > 0 and len(result['rows']) <= 5:
                        print(f"  Data: {json.dumps(result['rows'], indent=2)}")
                else:
                    print(f"  Response: {json.dumps(result, indent=2)[:500]}")
            else:
                print(f"  Response: {str(result)[:500]}")

            success_count += 1
        else:
            print(f"FAILED!")
            print(f"  Error: {response.text[:200]}")
            failed_count += 1

    except requests.exceptions.Timeout:
        print(f"TIMEOUT!")
        failed_count += 1
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        failed_count += 1

# Summary
print(f"\n\n{'=' * 80}")
print("QUERY TEST SUMMARY")
print(f"{'=' * 80}")
print(f"Total Tests: {len(test_queries)}")
print(f"Success: {success_count}")
print(f"Failed: {failed_count}")
print(f"Pass Rate: {success_count / len(test_queries) * 100:.1f}%")
print(f"\nOverall: {'PASS' if success_count == len(test_queries) else 'PARTIAL PASS' if success_count > 0 else 'FAIL'}")
print("=" * 80)
