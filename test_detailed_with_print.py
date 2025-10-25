"""
Detailed test with full request/response printing
Tests e-commerce sales data with complex queries
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

def print_request(method, url, payload=None, files=None):
    print("\n" + "="*80)
    print(f"REQUEST: {method} {url}")
    print("="*80)
    if payload:
        print("Payload:")
        print(json.dumps(payload, indent=2))
    if files:
        print(f"Files: {files}")

def print_response(response, show_full=False):
    print("\n" + "-"*80)
    print("RESPONSE:")
    print("-"*80)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    content_type = response.headers.get('content-type', '')

    if 'application/json' in content_type:
        try:
            data = response.json()
            if show_full:
                print("\nFull JSON Response:")
                print(json.dumps(data, indent=2))
            else:
                print("\nJSON Response (truncated):")
                print(json.dumps(data, indent=2)[:1000])
                if len(json.dumps(data)) > 1000:
                    print("... (truncated)")
        except:
            print(f"\nText Response: {response.text[:500]}")
    elif 'text/html' in content_type:
        print(f"\nHTML Response: {len(response.text)} bytes")
        print(f"Preview: {response.text[:200]}...")
    else:
        print(f"\nResponse: {response.text[:500]}")

print("="*80)
print("DETAILED H2SQL ENDPOINT TESTS WITH E-COMMERCE DATA")
print("="*80)

# ============================================================================
# Step 1: Upload e-commerce sales data
# ============================================================================
print("\n\nSTEP 1: UPLOAD E-COMMERCE SALES DATA")
print("="*80)

file_path = "D:\\testing-files\\ecom_sales.csv"
url = f"{BASE_URL}/upload"

print_request("POST", url, files={"file": "ecom_sales.csv"})

with open(file_path, 'rb') as f:
    files = {'file': ('ecom_sales.csv', f, 'text/csv')}
    data = {'project_id': PROJECT_ID}

    response = requests.post(url, files=files, data=data, timeout=300)
    print_response(response, show_full=True)

# ============================================================================
# Step 2: Complex Query - Sales by Category
# ============================================================================
print("\n\nSTEP 2: COMPLEX QUERY - Total Sales by Product Category")
print("="*80)

payload = {
    "project_id": PROJECT_ID,
    "question": "what is the total sales amount for each product category?"
}

url = f"{BASE_URL}/executequey"
print_request("POST", url, payload)

start = time.time()
response = requests.post(url, json=payload, timeout=300)
elapsed = time.time() - start

print(f"\nExecution Time: {elapsed:.2f}s")
print_response(response, show_full=True)

# ============================================================================
# Step 3: Comparison Query - Top Customers
# ============================================================================
print("\n\nSTEP 3: COMPARISON QUERY - Top 5 Customers by Total Spend")
print("="*80)

payload = {
    "project_id": PROJECT_ID,
    "question": "who are the top 5 customers by total amount spent?"
}

url = f"{BASE_URL}/executequey"
print_request("POST", url, payload)

start = time.time()
response = requests.post(url, json=payload, timeout=300)
elapsed = time.time() - start

print(f"\nExecution Time: {elapsed:.2f}s")
print_response(response, show_full=True)

# ============================================================================
# Step 4: Group By Query - Orders by Country
# ============================================================================
print("\n\nSTEP 4: GROUP BY QUERY - Order Count by Country")
print("="*80)

payload = {
    "project_id": PROJECT_ID,
    "question": "how many orders were placed from each country?"
}

url = f"{BASE_URL}/executequey"
print_request("POST", url, payload)

start = time.time()
response = requests.post(url, json=payload, timeout=300)
elapsed = time.time() - start

print(f"\nExecution Time: {elapsed:.2f}s")
print_response(response, show_full=True)

# ============================================================================
# Step 5: Complex Aggregation - Average Order Value by Payment Method
# ============================================================================
print("\n\nSTEP 5: AGGREGATION QUERY - Average Order Value by Payment Method")
print("="*80)

payload = {
    "project_id": PROJECT_ID,
    "question": "what is the average order amount for each payment method?"
}

url = f"{BASE_URL}/executequey"
print_request("POST", url, payload)

start = time.time()
response = requests.post(url, json=payload, timeout=300)
elapsed = time.time() - start

print(f"\nExecution Time: {elapsed:.2f}s")
print_response(response, show_full=True)

# ============================================================================
# Step 6: Generate Report
# ============================================================================
print("\n\nSTEP 6: GENERATE REPORT - Sales by Category")
print("="*80)

payload = {
    "projectId": PROJECT_ID,
    "question": "show me total sales by product category"
}

url = f"{BASE_URL}/generatereport"
print_request("POST", url, payload)

start = time.time()
response = requests.post(url, json=payload, timeout=300)
elapsed = time.time() - start

print(f"\nExecution Time: {elapsed:.2f}s")
print_response(response, show_full=False)

# ============================================================================
# Step 7: Graph Generation
# ============================================================================
print("\n\nSTEP 7: GRAPH GENERATION - Using response_id")
print("="*80)

# First get response_id
payload = {
    "project_id": PROJECT_ID,
    "question": "show sales by product category"
}

url = f"{BASE_URL}/executequey"
print_request("POST", url, payload)

response = requests.post(url, json=payload, timeout=300)
print_response(response, show_full=False)

if response.status_code == 200:
    result = response.json()
    response_id = result.get('response_id')

    if response_id:
        print(f"\n\nObtained response_id: {response_id}")
        print("\nNow calling /graph endpoint...")

        payload = {
            "project_id": PROJECT_ID,
            "response_id": response_id
        }

        url = f"{BASE_URL}/graph"
        print_request("POST", url, payload)

        start = time.time()
        response = requests.post(url, json=payload, timeout=300)
        elapsed = time.time() - start

        print(f"\nExecution Time: {elapsed:.2f}s")
        print_response(response, show_full=True)

print("\n\n" + "="*80)
print("ALL TESTS COMPLETE")
print("="*80)
