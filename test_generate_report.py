"""
Test Generate Report Endpoint

Tests the /h2s/data-upload/generatereport endpoint with uploaded data
"""
import requests
import json

url = "http://localhost:11901/h2s/data-upload/generatereport"
project_id = 22  # Using our test project with uploaded files

# Test questions based on uploaded files
test_questions = [
    {
        "name": "Customer count by city",
        "question": "get all the customers city and state count"
    },
    {
        "name": "Customer segments",
        "question": "show me customer segments and their counts"
    },
    {
        "name": "Top 10 customers",
        "question": "show me top 10 customers with their details"
    },
    {
        "name": "Customer roles distribution",
        "question": "what are the different customer roles and how many in each role"
    },
    {
        "name": "Employee department summary",
        "question": "show me employees grouped by department with count"
    },
    {
        "name": "Customer postal codes",
        "question": "get customers grouped by postal code with counts"
    }
]

print("=" * 80)
print("GENERATE REPORT ENDPOINT TEST")
print("=" * 80)
print(f"Endpoint: {url}")
print(f"Project ID: {project_id}")
print(f"\nTables available in project 22:")
print("  - CUSTOMERS_59C96545 (793 rows)")
print("  - CUSTOMERROLE_2857A605 (207 rows)")
print("  - EMPLOYEES_WITH_NORMAL_HEADINGS_07A68017 (39 rows)")
print()

success_count = 0
failed_count = 0
results = []

for i, test in enumerate(test_questions, 1):
    print(f"\n{'=' * 80}")
    print(f"Test {i}/{len(test_questions)}: {test['name']}")
    print(f"{'=' * 80}")
    print(f"Question: {test['question']}")

    try:
        payload = {
            "projectId": project_id,
            "question": test["question"]
        }

        print(f"\nSending request...")
        response = requests.post(url, json=payload, timeout=60)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nSUCCESS!")

            # Check what's in the response
            if isinstance(result, dict):
                print(f"\nResponse keys: {list(result.keys())}")

                # Display SQL if present
                if 'sql' in result:
                    print(f"\nGenerated SQL:")
                    print(f"  {result['sql'][:200]}...")

                # Display data summary if present
                if 'data' in result and isinstance(result['data'], dict):
                    if 'rows' in result['data']:
                        print(f"\nData rows returned: {len(result['data']['rows'])}")
                        if len(result['data']['rows']) > 0 and len(result['data']['rows']) <= 5:
                            print(f"Sample data:")
                            for row in result['data']['rows'][:3]:
                                print(f"  {row}")

                # Display HTML if present
                if 'html' in result:
                    html_len = len(result['html'])
                    print(f"\nHTML visualization: {html_len} characters")
                    if html_len > 0:
                        print(f"HTML preview: {result['html'][:150]}...")

                # Display full response if small
                response_str = json.dumps(result, indent=2)
                if len(response_str) < 500:
                    print(f"\nFull response:")
                    print(response_str)
            else:
                print(f"\nResponse: {str(result)[:500]}")

            results.append({
                "test": test['name'],
                "status": "SUCCESS",
                "has_sql": 'sql' in result if isinstance(result, dict) else False,
                "has_data": 'data' in result if isinstance(result, dict) else False,
                "has_html": 'html' in result if isinstance(result, dict) else False
            })
            success_count += 1

        else:
            print(f"\nFAILED!")
            error_text = response.text[:500]
            print(f"Error: {error_text}")

            # Try to parse error as JSON
            try:
                error_json = response.json()
                if 'detail' in error_json:
                    print(f"\nError detail: {error_json['detail'][:300]}")
            except:
                pass

            results.append({
                "test": test['name'],
                "status": "FAILED",
                "status_code": response.status_code,
                "error": error_text[:100]
            })
            failed_count += 1

    except requests.exceptions.Timeout:
        print(f"\nTIMEOUT: Request took longer than 60 seconds")
        results.append({
            "test": test['name'],
            "status": "TIMEOUT"
        })
        failed_count += 1

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
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
print(f"Total Tests: {len(test_questions)}")
print(f"Success: {success_count}")
print(f"Failed: {failed_count}")
print(f"Pass Rate: {success_count / len(test_questions) * 100:.1f}%")

print(f"\n\nDetailed Results:")
print("-" * 80)
for r in results:
    status_symbol = "OK:" if r['status'] == 'SUCCESS' else "ERROR:"
    print(f"{status_symbol} {r['test']}")
    print(f"  Status: {r['status']}")
    if r['status'] == 'SUCCESS':
        print(f"  Has SQL: {r.get('has_sql', False)}")
        print(f"  Has Data: {r.get('has_data', False)}")
        print(f"  Has HTML: {r.get('has_html', False)}")
    elif 'error' in r:
        print(f"  Error: {r['error']}")
    print()

print("=" * 80)
print(f"Overall: {'PASS' if success_count == len(test_questions) else 'PARTIAL PASS' if success_count > 0 else 'FAIL'}")
print("=" * 80)
