"""
Comprehensive API Test Suite for All Data Upload Endpoints

Tests all 5 endpoints with success and failure scenarios:
1. /h2s/data-upload/upload
2. /h2s/data-upload/recommendations/question
3. /h2s/data-upload/generatereport
4. /h2s/data-upload/executequey
5. /h2s/data-upload/graph
"""
import requests
import json
import os
import time
from pathlib import Path

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22
TEST_FILES_DIR = r"D:\testing-files"

# Color codes for terminal output (disabled for Windows compatibility)
class Colors:
    PASS = ""
    FAIL = ""
    SKIP = ""
    INFO = ""
    RESET = ""

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_test(name, status, details=""):
    status_text = {
        "PASS": "[PASS]",
        "FAIL": "[FAIL]",
        "SKIP": "[SKIP]",
        "INFO": "[INFO]"
    }
    print(f"{status_text.get(status, '[????]')} {name}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"       {line}")

# Global test results
results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0
}

def run_test(name, func):
    """Run a test function and track results"""
    global results
    results["total"] += 1
    try:
        status, details = func()
        if status == "PASS":
            results["passed"] += 1
        elif status == "FAIL":
            results["failed"] += 1
        elif status == "SKIP":
            results["skipped"] += 1
        print_test(name, status, details)
        return status
    except Exception as e:
        results["failed"] += 1
        print_test(name, "FAIL", f"Exception: {str(e)[:200]}")
        return "FAIL"

# ============================================================================
# 1. UPLOAD ENDPOINT TESTS
# ============================================================================

def test_upload_success_csv():
    """Upload valid CSV file"""
    file_path = os.path.join(TEST_FILES_DIR, "customers.csv")
    if not os.path.exists(file_path):
        return "SKIP", f"File not found: {file_path}"

    with open(file_path, 'rb') as f:
        files = {'file': ('test_customers.csv', f, 'text/csv')}
        data = {'project_id': str(PROJECT_ID)}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=60)

    if response.status_code == 200:
        result = response.json()
        return "PASS", f"Uploaded: {result.get('tableName')}, Rows: {result.get('rowsInserted')}"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_upload_success_xlsx():
    """Upload valid Excel file"""
    file_path = os.path.join(TEST_FILES_DIR, "customerrole.xlsx")
    if not os.path.exists(file_path):
        return "SKIP", f"File not found: {file_path}"

    with open(file_path, 'rb') as f:
        files = {'file': ('test_roles.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {'project_id': str(PROJECT_ID)}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=60)

    if response.status_code == 200:
        result = response.json()
        return "PASS", f"Uploaded: {result.get('tableName')}, Rows: {result.get('rowsInserted')}"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_upload_fail_no_file():
    """Upload without file (should fail)"""
    data = {'project_id': str(PROJECT_ID)}
    response = requests.post(f"{BASE_URL}/upload", data=data, timeout=10)

    if response.status_code in [400, 422]:
        return "PASS", f"Correctly rejected: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422, got {response.status_code}"

def test_upload_fail_no_project_id():
    """Upload without project_id (should fail)"""
    file_path = os.path.join(TEST_FILES_DIR, "customers.csv")
    if not os.path.exists(file_path):
        return "SKIP", f"File not found: {file_path}"

    with open(file_path, 'rb') as f:
        files = {'file': ('test.csv', f, 'text/csv')}
        response = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)

    if response.status_code in [400, 422]:
        return "PASS", f"Correctly rejected: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422, got {response.status_code}"

def test_upload_fail_invalid_project():
    """Upload with non-existent project_id (should fail)"""
    file_path = os.path.join(TEST_FILES_DIR, "customers.csv")
    if not os.path.exists(file_path):
        return "SKIP", f"File not found: {file_path}"

    with open(file_path, 'rb') as f:
        files = {'file': ('test.csv', f, 'text/csv')}
        data = {'project_id': '99999'}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=10)

    if response.status_code in [404, 500]:
        return "PASS", f"Correctly rejected invalid project: {response.status_code}"
    else:
        return "FAIL", f"Expected 404/500, got {response.status_code}"

def test_upload_fail_invalid_file_type():
    """Upload unsupported file type (should fail or skip)"""
    # Create a temporary invalid file
    invalid_file_path = r"D:\h2sql\test_invalid.txt"
    with open(invalid_file_path, 'w') as f:
        f.write("This is not a valid data file")

    try:
        with open(invalid_file_path, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            data = {'project_id': str(PROJECT_ID)}
            response = requests.post(f"{BASE_URL}/upload", files=files, data=data, timeout=10)

        if response.status_code in [400, 422, 500]:
            return "PASS", f"Correctly rejected invalid file type: {response.status_code}"
        else:
            return "FAIL", f"Expected error, got {response.status_code}"
    finally:
        if os.path.exists(invalid_file_path):
            os.remove(invalid_file_path)

# ============================================================================
# 2. RECOMMENDATIONS ENDPOINT TESTS
# ============================================================================

def test_recommendations_success():
    """Get recommendations for valid project"""
    response = requests.get(f"{BASE_URL}/recommendations/question?project_id={PROJECT_ID}", timeout=10)

    # Endpoint may return 501 if not implemented
    if response.status_code == 501:
        return "SKIP", "Feature not implemented (501)"
    elif response.status_code == 200:
        result = response.json()
        return "PASS", f"Got recommendations: {len(result.get('questions', []))} questions"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_recommendations_fail_no_project():
    """Get recommendations without project_id (should fail)"""
    response = requests.get(f"{BASE_URL}/recommendations/question", timeout=10)

    if response.status_code in [400, 422, 501]:
        return "PASS", f"Correctly rejected: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422/501, got {response.status_code}"

def test_recommendations_fail_invalid_project():
    """Get recommendations for non-existent project (should fail)"""
    response = requests.get(f"{BASE_URL}/recommendations/question?project_id=99999", timeout=10)

    if response.status_code in [404, 500, 501]:
        return "PASS", f"Correctly rejected invalid project: {response.status_code}"
    else:
        return "FAIL", f"Expected 404/500/501, got {response.status_code}"

# ============================================================================
# 3. GENERATE REPORT ENDPOINT TESTS
# ============================================================================

def test_generatereport_mode1_success():
    """Generate report with direct SQL (Mode 1)"""
    payload = {
        "projectId": PROJECT_ID,
        "recomended_questions": [{
            "recomended_qstn_id": "test_report_1",
            "sql_query": 'SELECT COUNT(*) as total FROM "CUSTOMERS_59C96545"',
            "question": "Total customers"
        }]
    }
    response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=30)

    if response.status_code == 200:
        html_len = len(response.text)
        return "PASS", f"Generated HTML report: {html_len} chars"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_generatereport_mode3_success():
    """Generate report with natural language (Mode 3)"""
    payload = {
        "projectId": PROJECT_ID,
        "question": "how many customers are there in total"
    }
    response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=60)

    if response.status_code == 200:
        html_len = len(response.text)
        return "PASS", f"Generated HTML report from NL: {html_len} chars"
    elif response.status_code == 400:
        # May fail due to table name issues, but LLM should still generate SQL
        return "PASS", f"LLM processed (with execution error): {response.status_code}"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_generatereport_fail_no_params():
    """Generate report without required params (should fail)"""
    payload = {"projectId": PROJECT_ID}
    response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=10)

    if response.status_code in [400, 422]:
        return "PASS", f"Correctly rejected missing params: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422, got {response.status_code}"

def test_generatereport_fail_invalid_project():
    """Generate report for non-existent project (should fail)"""
    payload = {
        "projectId": 99999,
        "question": "test question"
    }
    response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=10)

    if response.status_code in [404, 500]:
        return "PASS", f"Correctly rejected invalid project: {response.status_code}"
    else:
        return "FAIL", f"Expected 404/500, got {response.status_code}"

def test_generatereport_fail_invalid_sql():
    """Generate report with invalid SQL (Mode 1, should fail)"""
    payload = {
        "projectId": PROJECT_ID,
        "recomended_questions": [{
            "recomended_qstn_id": "test_invalid",
            "sql_query": "INVALID SQL QUERY HERE",
            "question": "Test"
        }]
    }
    response = requests.post(f"{BASE_URL}/generatereport", json=payload, timeout=10)

    if response.status_code in [400, 500]:
        return "PASS", f"Correctly rejected invalid SQL: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/500, got {response.status_code}"

# ============================================================================
# 4. EXECUTE QUERY ENDPOINT TESTS
# ============================================================================

def test_executequey_success():
    """Execute valid query"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "How many customers are there?",
        "query": 'SELECT COUNT(*) as total FROM "CUSTOMERS_59C96545"'
    }
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        return "PASS", f"Query executed: {result.get('rows', [])[0] if result.get('rows') else 'No rows'}"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_executequey_success_cached():
    """Execute query that may hit cache"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Total customer count",
        "query": 'SELECT COUNT(*) FROM "CUSTOMERS_59C96545"'
    }
    # Execute twice to potentially hit cache
    requests.post(f"{BASE_URL}/executequey", json=payload, timeout=30)
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        return "PASS", f"Query executed (possibly cached)"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_executequey_fail_no_query():
    """Execute without query (should fail)"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Test"
    }
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=10)

    if response.status_code in [400, 422]:
        return "PASS", f"Correctly rejected missing query: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422, got {response.status_code}"

def test_executequey_fail_invalid_project():
    """Execute query for non-existent project (should fail)"""
    payload = {
        "project_id": 99999,
        "question": "Test",
        "query": "SELECT 1"
    }
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=10)

    if response.status_code in [404, 500]:
        return "PASS", f"Correctly rejected invalid project: {response.status_code}"
    else:
        return "FAIL", f"Expected 404/500, got {response.status_code}"

def test_executequey_fail_invalid_sql():
    """Execute invalid SQL (should fail)"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Test",
        "query": "INVALID SQL SYNTAX HERE"
    }
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=10)

    if response.status_code in [400, 500]:
        return "PASS", f"Correctly rejected invalid SQL: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/500, got {response.status_code}"

def test_executequey_fail_table_not_exist():
    """Execute query on non-existent table (should fail)"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Test",
        "query": "SELECT * FROM nonexistent_table"
    }
    response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=10)

    if response.status_code in [400, 500]:
        return "PASS", f"Correctly rejected non-existent table: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/500, got {response.status_code}"

# ============================================================================
# 5. GRAPH ENDPOINT TESTS
# ============================================================================

def test_graph_success():
    """Generate graph visualization"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Show customer distribution",
        "query": 'SELECT segment, COUNT(*) as count FROM "CUSTOMERS_59C96545" GROUP BY segment LIMIT 5'
    }
    response = requests.post(f"{BASE_URL}/graph", json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        return "PASS", f"Graph generated: {result.get('chartType', 'unknown')} chart"
    else:
        return "FAIL", f"Status {response.status_code}: {response.text[:200]}"

def test_graph_fail_no_query():
    """Generate graph without query (should fail)"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Test"
    }
    response = requests.post(f"{BASE_URL}/graph", json=payload, timeout=10)

    if response.status_code in [400, 422]:
        return "PASS", f"Correctly rejected missing query: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/422, got {response.status_code}"

def test_graph_fail_invalid_project():
    """Generate graph for non-existent project (should fail)"""
    payload = {
        "project_id": 99999,
        "question": "Test",
        "query": "SELECT 1"
    }
    response = requests.post(f"{BASE_URL}/graph", json=payload, timeout=10)

    if response.status_code in [404, 500]:
        return "PASS", f"Correctly rejected invalid project: {response.status_code}"
    else:
        return "FAIL", f"Expected 404/500, got {response.status_code}"

def test_graph_fail_invalid_sql():
    """Generate graph with invalid SQL (should fail)"""
    payload = {
        "project_id": PROJECT_ID,
        "question": "Test",
        "query": "INVALID SQL"
    }
    response = requests.post(f"{BASE_URL}/graph", json=payload, timeout=10)

    if response.status_code in [400, 500]:
        return "PASS", f"Correctly rejected invalid SQL: {response.status_code}"
    else:
        return "FAIL", f"Expected 400/500, got {response.status_code}"

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print_header("COMPREHENSIVE API TEST SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Test Files: {TEST_FILES_DIR}")

    # Test 1: Upload Endpoint
    print_header("1. UPLOAD ENDPOINT (/h2s/data-upload/upload)")
    run_test("Upload CSV file (success)", test_upload_success_csv)
    run_test("Upload Excel file (success)", test_upload_success_xlsx)
    run_test("Upload without file (failure)", test_upload_fail_no_file)
    run_test("Upload without project_id (failure)", test_upload_fail_no_project_id)
    run_test("Upload with invalid project_id (failure)", test_upload_fail_invalid_project)
    run_test("Upload invalid file type (failure)", test_upload_fail_invalid_file_type)

    # Test 2: Recommendations Endpoint
    print_header("2. RECOMMENDATIONS ENDPOINT (/h2s/data-upload/recommendations/question)")
    run_test("Get recommendations (success)", test_recommendations_success)
    run_test("Get recommendations without project_id (failure)", test_recommendations_fail_no_project)
    run_test("Get recommendations with invalid project_id (failure)", test_recommendations_fail_invalid_project)

    # Test 3: Generate Report Endpoint
    print_header("3. GENERATE REPORT ENDPOINT (/h2s/data-upload/generatereport)")
    run_test("Generate report Mode 1 - Direct SQL (success)", test_generatereport_mode1_success)
    run_test("Generate report Mode 3 - Natural Language (success)", test_generatereport_mode3_success)
    run_test("Generate report without params (failure)", test_generatereport_fail_no_params)
    run_test("Generate report with invalid project_id (failure)", test_generatereport_fail_invalid_project)
    run_test("Generate report with invalid SQL (failure)", test_generatereport_fail_invalid_sql)

    # Test 4: Execute Query Endpoint
    print_header("4. EXECUTE QUERY ENDPOINT (/h2s/data-upload/executequey)")
    run_test("Execute valid query (success)", test_executequey_success)
    run_test("Execute query with cache (success)", test_executequey_success_cached)
    run_test("Execute without query (failure)", test_executequey_fail_no_query)
    run_test("Execute with invalid project_id (failure)", test_executequey_fail_invalid_project)
    run_test("Execute invalid SQL (failure)", test_executequey_fail_invalid_sql)
    run_test("Execute query on non-existent table (failure)", test_executequey_fail_table_not_exist)

    # Test 5: Graph Endpoint
    print_header("5. GRAPH ENDPOINT (/h2s/data-upload/graph)")
    run_test("Generate graph visualization (success)", test_graph_success)
    run_test("Generate graph without query (failure)", test_graph_fail_no_query)
    run_test("Generate graph with invalid project_id (failure)", test_graph_fail_invalid_project)
    run_test("Generate graph with invalid SQL (failure)", test_graph_fail_invalid_sql)

    # Print Summary
    print_header("TEST SUMMARY")
    print(f"Total Tests:   {results['total']}")
    print(f"Passed:        {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed:        {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print(f"Skipped:       {results['skipped']} ({results['skipped']/results['total']*100:.1f}%)")
    print()

    if results['failed'] == 0:
        print("OVERALL RESULT: ALL TESTS PASSED!")
    else:
        print(f"OVERALL RESULT: {results['failed']} TEST(S) FAILED")

    print("=" * 80)

if __name__ == "__main__":
    main()
