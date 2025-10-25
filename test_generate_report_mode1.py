"""
Test Generate Report - Mode 1 (Direct SQL)

Tests the generatereport endpoint with direct SQL queries,
bypassing the LLM to avoid unicode encoding issues.
"""
import requests
import json

url = "http://localhost:11901/h2s/data-upload/generatereport"
project_id = 22

# Mode 1: Provide SQL queries directly
test_cases = [
    {
        "name": "Count customers by city",
        "request": {
            "projectId": project_id,
            "recomended_questions": [
                {
                    "recomended_qstn_id": "test_1",
                    "sql_query": "SELECT city, state, COUNT(*) as customer_count FROM \"CUSTOMERS_59C96545\" GROUP BY city, state ORDER BY customer_count DESC LIMIT 10",
                    "question": "Get customer count by city and state"
                }
            ]
        }
    },
    {
        "name": "Customer segments distribution",
        "request": {
            "projectId": project_id,
            "recomended_questions": [
                {
                    "recomended_qstn_id": "test_2",
                    "sql_query": "SELECT segment, COUNT(*) as count FROM \"CUSTOMERS_59C96545\" GROUP BY segment ORDER BY count DESC",
                    "question": "Show customer segments"
                }
            ]
        }
    },
    {
        "name": "Top 5 customers by ID",
        "request": {
            "projectId": project_id,
            "recomended_questions": [
                {
                    "recomended_qstn_id": "test_3",
                    "sql_query": "SELECT customer_id, customer_name, city, state, segment FROM \"CUSTOMERS_59C96545\" LIMIT 5",
                    "question": "Show top 5 customers"
                }
            ]
        }
    },
    {
        "name": "Customer roles count",
        "request": {
            "projectId": project_id,
            "recomended_questions": [
                {
                    "recomended_qstn_id": "test_4",
                    "sql_query": "SELECT COUNT(*) as total_roles FROM \"CUSTOMERROLE_2857A605\"",
                    "question": "Total customer roles"
                }
            ]
        }
    },
    {
        "name": "Employee count",
        "request": {
            "projectId": project_id,
            "recomended_questions": [
                {
                    "recomended_qstn_id": "test_5",
                    "sql_query": "SELECT COUNT(*) as total_employees FROM \"EMPLOYEES_WITH_NORMAL_HEADINGS_07A68017\"",
                    "question": "Total employees"
                }
            ]
        }
    }
]

print("=" * 80)
print("GENERATE REPORT TEST - MODE 1 (Direct SQL)")
print("=" * 80)
print(f"Endpoint: {url}")
print(f"Project ID: {project_id}")
print(f"Mode: Provide SQL queries directly (bypass LLM)")
print()

success_count = 0
failed_count = 0
results = []

for i, test in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"Test {i}/{len(test_cases)}: {test['name']}")
    print(f"{'=' * 80}")

    sql_query = test["request"]["recomended_questions"][0]["sql_query"]
    print(f"SQL: {sql_query[:80]}...")

    try:
        response = requests.post(url, json=test["request"], timeout=60)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS!")

            # Analyze response
            response_keys = list(result.keys()) if isinstance(result, dict) else []
            print(f"Response keys: {response_keys}")

            has_data = False
            row_count = 0

            if 'data' in result and isinstance(result['data'], dict):
                if 'rows' in result['data']:
                    row_count = len(result['data']['rows'])
                    has_data = True
                    print(f"Data rows: {row_count}")
                    if row_count > 0 and row_count <= 3:
                        print(f"Sample rows:")
                        for row in result['data']['rows'][:3]:
                            print(f"  {row}")

            has_html = 'html' in result
            html_size = len(result.get('html', '')) if has_html else 0
            print(f"Has HTML: {has_html} ({html_size} chars)")

            results.append({
                "test": test['name'],
                "status": "SUCCESS",
                "has_data": has_data,
                "row_count": row_count,
                "has_html": has_html,
                "html_size": html_size
            })
            success_count += 1

        else:
            print(f"FAILED!")
            error_text = response.text[:300]
            print(f"Error: {error_text}")

            results.append({
                "test": test['name'],
                "status": "FAILED",
                "status_code": response.status_code,
                "error": error_text[:100]
            })
            failed_count += 1

    except requests.exceptions.Timeout:
        print(f"TIMEOUT!")
        results.append({
            "test": test['name'],
            "status": "TIMEOUT"
        })
        failed_count += 1

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        results.append({
            "test": test['name'],
            "status": "ERROR",
            "error": str(e)[:100]
        })
        failed_count += 1

# Summary
print(f"\n\n{'=' * 80}")
print("TEST SUMMARY")
print(f"{'=' * 80}")
print(f"Total Tests: {len(test_cases)}")
print(f"Success: {success_count}")
print(f"Failed: {failed_count}")
print(f"Pass Rate: {success_count / len(test_cases) * 100:.1f}%")

print(f"\n\nDetailed Results:")
print("-" * 80)
for r in results:
    status_symbol = "OK:" if r['status'] == 'SUCCESS' else "ERROR:"
    print(f"{status_symbol} {r['test']}")
    print(f"  Status: {r['status']}")
    if r['status'] == 'SUCCESS':
        print(f"  Has Data: {r.get('has_data')}, Rows: {r.get('row_count')}")
        print(f"  Has HTML: {r.get('has_html')}, Size: {r.get('html_size')} chars")
    elif 'error' in r:
        print(f"  Error: {r['error']}")
    print()

print("=" * 80)
overall = 'PASS' if success_count == len(test_cases) else 'PARTIAL PASS' if success_count > 0 else 'FAIL'
print(f"Overall: {overall}")
print("=" * 80)
