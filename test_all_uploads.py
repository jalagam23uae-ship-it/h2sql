"""
Comprehensive File Upload Test Script

Tests all files from D:\\testing-files directory
"""
import requests
import json
import os
from pathlib import Path

# Configuration
url = "http://localhost:11901/h2s/data-upload/upload"
project_id = "22"
test_files_dir = r"D:\testing-files"

# Get all test files
test_files = [
    "customers.csv",
    "customerrole.xlsx",
    "Employees_with_normal_headings.xlsx"
]

print("=" * 80)
print("FILE UPLOAD COMPREHENSIVE TEST")
print("=" * 80)
print(f"Endpoint: {url}")
print(f"Project ID: {project_id}")
print(f"Test Files Directory: {test_files_dir}\n")

results = []

for filename in test_files:
    file_path = os.path.join(test_files_dir, filename)

    print(f"\n{'=' * 80}")
    print(f"Testing: {filename}")
    print(f"{'=' * 80}")

    if not os.path.exists(file_path):
        print(f"SKIP: File not found: {file_path}")
        results.append({
            "file": filename,
            "status": "SKIP",
            "reason": "File not found"
        })
        continue

    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size:,} bytes")

    try:
        # Determine content type
        if filename.endswith('.csv'):
            content_type = 'text/csv'
        elif filename.endswith('.xlsx'):
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            content_type = 'application/octet-stream'

        # Upload file
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, content_type)}
            data = {'project_id': project_id}

            response = requests.post(url, files=files, data=data, timeout=120)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nSUCCESS!")
            print(f"  Table Name: {result.get('tableName')}")
            print(f"  Rows Inserted: {result.get('rowsInserted')}")
            print(f"  Message: {result.get('message')}")

            results.append({
                "file": filename,
                "status": "SUCCESS",
                "status_code": 200,
                "table_name": result.get('tableName'),
                "rows_inserted": result.get('rowsInserted')
            })
        else:
            print(f"\nFAILED!")
            print(f"Response: {response.text}")

            results.append({
                "file": filename,
                "status": "FAILED",
                "status_code": response.status_code,
                "error": response.text[:200]
            })

    except requests.exceptions.Timeout:
        print(f"\nTIMEOUT: Request took longer than 120 seconds")
        results.append({
            "file": filename,
            "status": "TIMEOUT",
            "reason": "Request timeout after 120s"
        })

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        results.append({
            "file": filename,
            "status": "ERROR",
            "reason": str(e)
        })

# Print summary
print(f"\n\n{'=' * 80}")
print("TEST SUMMARY")
print(f"{'=' * 80}\n")

success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
failed_count = sum(1 for r in results if r['status'] == 'FAILED')
error_count = sum(1 for r in results if r['status'] in ['ERROR', 'TIMEOUT', 'SKIP'])

print(f"Total Files: {len(results)}")
print(f"Success: {success_count}")
print(f"Failed: {failed_count}")
print(f"Errors: {error_count}\n")

print("Detailed Results:")
print("-" * 80)
for r in results:
    status_symbol = "OK:" if r['status'] == 'SUCCESS' else "ERROR:"
    print(f"{status_symbol} {r['file']}")
    print(f"  Status: {r['status']}")
    if r['status'] == 'SUCCESS':
        print(f"  Table: {r.get('table_name')}")
        print(f"  Rows: {r.get('rows_inserted')}")
    else:
        print(f"  Reason: {r.get('reason', r.get('error', 'Unknown'))}")
    print()

print("=" * 80)
print(f"Overall Result: {'PASS' if success_count == len(results) else 'PARTIAL PASS' if success_count > 0 else 'FAIL'}")
print("=" * 80)
