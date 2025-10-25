"""
Test the proper workflow: executequey -> graph
The response_id from executequey response is passed to graph endpoint
"""
import requests
import json

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

print("=" * 80)
print("TESTING: executequey -> graph workflow")
print("=" * 80)

# Step 1: Execute query to get response_id
print("\nStep 1: Execute query")
print("-" * 80)

execute_payload = {
    "project_id": PROJECT_ID,
    "question": "Show me customer distribution by segment",
    "query": 'SELECT "segment", COUNT(*) as count FROM "CUSTOMERS_59C96545" GROUP BY "segment" ORDER BY count DESC'
}

print(f"POST {BASE_URL}/executequey")
print(f"Payload: {json.dumps(execute_payload, indent=2)}")

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

        # Step 2: Use response_id to generate graph
        print("\n" + "=" * 80)
        print("Step 2: Generate graph using response_id")
        print("-" * 80)

        graph_payload = {
            "project_id": PROJECT_ID,
            "response_id": response_id,
            "question": "Show me customer distribution by segment",
            "query": execute_payload["query"]
        }

        print(f"POST {BASE_URL}/graph")
        print(f"Payload: {json.dumps(graph_payload, indent=2)}")

        graph_response = requests.post(f"{BASE_URL}/graph", json=graph_payload, timeout=30)

        print(f"\nStatus: {graph_response.status_code}")

        if graph_response.status_code == 200:
            graph_result = graph_response.json()
            print("\n[OK] Graph generated successfully!")
            print(f"Response keys: {list(graph_result.keys())}")

            # Display graph spec
            if 'chartType' in graph_result:
                print(f"\nChart Type: {graph_result.get('chartType')}")
                print(f"X Field: {graph_result.get('xField')}")
                print(f"Y Field: {graph_result.get('yField')}")
                print(f"Allowed Chart Types: {graph_result.get('chartTypes', [])}")

            print("\n[OK] WORKFLOW COMPLETE!")
            print("\nSummary:")
            print(f"  1. Query executed -> got response_id: {response_id}")
            print(f"  2. Graph generated -> chart type: {graph_result.get('chartType', 'N/A')}")

        else:
            print("\n[FAIL] Graph generation failed!")
            print(f"Error: {graph_response.text[:500]}")

    else:
        print("\n[FAIL] No response_id in executequey response!")
        print(f"Available keys: {list(result.keys())}")
        print(f"\nFull response: {json.dumps(result, indent=2)[:1000]}")

else:
    print(f"\n[FAIL] Query execution failed!")
    print(f"Error: {response.text[:500]}")

print("\n" + "=" * 80)
