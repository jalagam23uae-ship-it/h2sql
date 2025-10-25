"""
Comprehensive test of all H2SQL endpoints with new LLM configuration
LLM: http://192.168.1.6:3034/v1 - Llama-4-Scout-17B-16E-Instruct
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

# Test results tracker
results = {
    "upload": [],
    "generatereport": [],
    "executequey": [],
    "graph": [],
    "recommendations": []
}

print("=" * 80)
print("COMPREHENSIVE H2SQL ENDPOINT TESTS")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print(f"Project ID: {PROJECT_ID}")
print(f"LLM: http://192.168.1.6:3034/v1 - Llama-4-Scout-17B-16E-Instruct")
print("=" * 80)

# ============================================================================
# Test 1: Execute Query Endpoint
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: /executequey - Natural Language Query")
print("=" * 80)

test_queries = [
    "how many customers are in the database?",
    "show customer count by segment",
    "list top 5 cities by customer count"
]

for idx, question in enumerate(test_queries, 1):
    print(f"\nTest 1.{idx}: {question}")
    print("-" * 80)

    payload = {
        "project_id": PROJECT_ID,
        "question": question
    }

    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=300)
        elapsed = time.time() - start

        status = "PASS" if response.status_code == 200 else "FAIL"
        results["executequey"].append({
            "test": f"Query: {question}",
            "status": status,
            "time": f"{elapsed:.2f}s",
            "code": response.status_code
        })

        print(f"Status: {response.status_code} - {status}")
        print(f"Time: {elapsed:.2f}s")

        if response.status_code == 200:
            result = response.json()
            if 'llm_generated_sql' in result:
                print(f"SQL: {result['llm_generated_sql'][:200]}...")
            if 'db_result' in result:
                print(f"Rows: {len(result['db_result'])}")

    except Exception as e:
        elapsed = time.time() - start
        results["executequey"].append({
            "test": f"Query: {question}",
            "status": "ERROR",
            "time": f"{elapsed:.2f}s",
            "error": str(e)
        })
        print(f"ERROR after {elapsed:.2f}s: {str(e)[:100]}")

# ============================================================================
# Test 2: Generate Report Endpoint (Mode 3 - Natural Language)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: /generatereport - Natural Language Report")
print("=" * 80)

report_tests = [
    {
        "name": "Customer segment distribution",
        "question": "show me the distribution of customers by segment"
    },
    {
        "name": "Top cities",
        "question": "what are the top 10 cities by customer count?"
    }
]

for idx, test in enumerate(report_tests, 1):
    print(f"\nTest 2.{idx}: {test['name']}")
    print("-" * 80)

    payload = {
        "projectId": PROJECT_ID,
        "question": test['question']
    }

    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=300)
        elapsed = time.time() - start

        status = "PASS" if response.status_code == 200 else "FAIL"
        results["generatereport"].append({
            "test": test['name'],
            "status": status,
            "time": f"{elapsed:.2f}s",
            "code": response.status_code
        })

        print(f"Status: {response.status_code} - {status}")
        print(f"Time: {elapsed:.2f}s")

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            if 'text/html' in content_type:
                print(f"HTML size: {len(response.text)} bytes")

    except Exception as e:
        elapsed = time.time() - start
        results["generatereport"].append({
            "test": test['name'],
            "status": "ERROR",
            "time": f"{elapsed:.2f}s",
            "error": str(e)
        })
        print(f"ERROR after {elapsed:.2f}s: {str(e)[:100]}")

# ============================================================================
# Test 3: Graph Endpoint (using response_id from executequey)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: /graph - Graph Generation from response_id")
print("=" * 80)

print("\nTest 3.1: Execute query first to get response_id")
print("-" * 80)

execute_payload = {
    "project_id": PROJECT_ID,
    "question": "count customers by segment"
}

try:
    exec_response = requests.post(f"{BASE_URL}/executequey", json=execute_payload, timeout=300)

    if exec_response.status_code == 200:
        exec_result = exec_response.json()
        response_id = exec_result.get('response_id')

        if response_id:
            print(f"Response ID obtained: {response_id}")

            # Now test graph endpoint
            print("\nTest 3.2: Generate graph using response_id")
            print("-" * 80)

            graph_payload = {
                "project_id": PROJECT_ID,
                "response_id": response_id
            }

            start = time.time()
            graph_response = requests.post(f"{BASE_URL}/graph", json=graph_payload, timeout=300)
            elapsed = time.time() - start

            status = "PASS" if graph_response.status_code == 200 else "FAIL"
            results["graph"].append({
                "test": "Graph from response_id",
                "status": status,
                "time": f"{elapsed:.2f}s",
                "code": graph_response.status_code
            })

            print(f"Status: {graph_response.status_code} - {status}")
            print(f"Time: {elapsed:.2f}s")

            if graph_response.status_code == 200:
                content_type = graph_response.headers.get('content-type', '')
                print(f"Content-Type: {content_type}")

        else:
            results["graph"].append({
                "test": "Graph from response_id",
                "status": "FAIL",
                "error": "No response_id in executequey response"
            })
            print("FAIL: No response_id in executequey response")
    else:
        results["graph"].append({
            "test": "Graph from response_id",
            "status": "FAIL",
            "error": f"Executequey failed: {exec_response.status_code}"
        })
        print(f"FAIL: Executequey failed with status {exec_response.status_code}")

except Exception as e:
    results["graph"].append({
        "test": "Graph from response_id",
        "status": "ERROR",
        "error": str(e)
    })
    print(f"ERROR: {str(e)[:100]}")

# ============================================================================
# Test 4: Upload Endpoint (using test file)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: /upload - File Upload")
print("=" * 80)

# Check if test file exists
import os
test_file = "D:\\testing-files\\customers.csv"

if os.path.exists(test_file):
    print(f"\nTest 4.1: Upload CSV file")
    print("-" * 80)
    print(f"File: {test_file}")

    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test_customers.csv', f, 'text/csv')}
            data = {'project_id': PROJECT_ID}

            start = time.time()
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=300)
            elapsed = time.time() - start

            status = "PASS" if response.status_code == 200 else "FAIL"
            results["upload"].append({
                "test": "Upload CSV",
                "status": status,
                "time": f"{elapsed:.2f}s",
                "code": response.status_code
            })

            print(f"Status: {response.status_code} - {status}")
            print(f"Time: {elapsed:.2f}s")

            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:200]}...")

    except Exception as e:
        results["upload"].append({
            "test": "Upload CSV",
            "status": "ERROR",
            "error": str(e)
        })
        print(f"ERROR: {str(e)[:100]}")
else:
    results["upload"].append({
        "test": "Upload CSV",
        "status": "SKIP",
        "reason": "Test file not found"
    })
    print(f"SKIP: Test file not found at {test_file}")

# ============================================================================
# Test 5: Recommendations Endpoint
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: /recommendations/question - Get Recommendations")
print("=" * 80)

print("\nTest 5.1: Get question recommendations")
print("-" * 80)

rec_payload = {
    "project_id": PROJECT_ID
}

start = time.time()
try:
    response = requests.post(f"{BASE_URL}/recommendations/question", json=rec_payload, timeout=300)
    elapsed = time.time() - start

    status = "PASS" if response.status_code == 200 else "FAIL"
    results["recommendations"].append({
        "test": "Get recommendations",
        "status": status,
        "time": f"{elapsed:.2f}s",
        "code": response.status_code
    })

    print(f"Status: {response.status_code} - {status}")
    print(f"Time: {elapsed:.2f}s")

    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)[:200]}...")

except Exception as e:
    elapsed = time.time() - start
    results["recommendations"].append({
        "test": "Get recommendations",
        "status": "ERROR",
        "time": f"{elapsed:.2f}s",
        "error": str(e)
    })
    print(f"ERROR after {elapsed:.2f}s: {str(e)[:100]}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = 0
passed_tests = 0

for endpoint, tests in results.items():
    if tests:
        print(f"\n{endpoint.upper()}: {len(tests)} tests")
        for test in tests:
            total_tests += 1
            status_icon = "[PASS]" if test['status'] == "PASS" else "[FAIL]" if test['status'] == "FAIL" else "[ERROR]" if test['status'] == "ERROR" else "[SKIP]"
            print(f"  {status_icon} {test['test']}")
            if test['status'] == "PASS":
                passed_tests += 1
                if 'time' in test:
                    print(f"      Time: {test['time']}, Status: {test.get('code', 'N/A')}")
            elif 'error' in test:
                print(f"      Error: {test['error'][:80]}")

print("\n" + "=" * 80)
print(f"TOTAL: {passed_tests}/{total_tests} tests passed ({passed_tests*100//total_tests if total_tests > 0 else 0}%)")
print("=" * 80)
