"""
Test script for file upload endpoint
Uploads customers.csv to project ID 22
"""
import requests
import json

# Configuration
url = "http://localhost:11901/h2s/data-upload/upload"
file_path = r"D:\testing-files\customers.csv"
project_id = "22"

print(f"Uploading {file_path} to project {project_id}...")
print(f"Endpoint: {url}\n")

try:
    # Open file and prepare multipart form data
    with open(file_path, 'rb') as f:
        files = {'file': ('customers.csv', f, 'text/csv')}
        data = {'project_id': project_id}

        response = requests.post(url, files=files, data=data)

    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")

    if response.status_code == 200:
        print("SUCCESS!")
        result = response.json()
        print(json.dumps(result, indent=2))
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)

except FileNotFoundError:
    print(f"ERROR: File not found: {file_path}")
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to server. Is it running?")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
