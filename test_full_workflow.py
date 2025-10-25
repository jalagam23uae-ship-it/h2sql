"""
Test complete executequey -> graph workflow
Step 1: Natural language query via executequey
Step 2: Visualization via graph using response_id from step 1
"""
import requests
import json

BASE_URL = "http://localhost:11901/h2s/data-upload"
PROJECT_ID = 22

print("=" * 80)
print("TESTING: Complete executequey -> graph workflow")
print("=" * 80)

# Step 1: Execute query with natural language
print("\nStep 1: Execute query with natural language")
print("-" * 80)

execute_payload = {
    "project_id": PROJECT_ID,
    "question": "show me employees count by job title"
}

print(f"POST {BASE_URL}/executequey")
print(f"Payload: {json.dumps(execute_payload, indent=2)}")

try:
    response = requests.post(f"{BASE_URL}/executequey", json=execute_payload, timeout=60)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\n[OK] Query executed successfully!")

        # Check for response_id
        if 'response_id' not in result:
            print("\n[FAIL] No response_id in response!")
            print(f"Available keys: {list(result.keys())}")
            exit(1)

        response_id = result['response_id']
        print(f"\n[OK] Got response_id: {response_id}")

        # Display LLM-generated SQL
        if 'llm_generated_sql' in result:
            print(f"\nLLM-generated SQL:\n{result['llm_generated_sql']}")

        # Display results
        if 'db_result' in result:
            print(f"\nQuery returned {len(result['db_result'])} rows")
            # Skip printing rows due to Unicode issues with Arabic characters

        # Step 2: Generate graph using response_id
        print("\n" + "=" * 80)
        print("Step 2: Generate graph visualization")
        print("-" * 80)

        graph_payload = {
            "project_id": PROJECT_ID,
            "response_id": response_id
        }

        print(f"POST {BASE_URL}/graph")
        print(f"Payload: {json.dumps(graph_payload, indent=2)}")

        graph_response = requests.post(f"{BASE_URL}/graph", json=graph_payload, timeout=60)

        print(f"\nStatus: {graph_response.status_code}")

        if graph_response.status_code == 200:
            # Check if response is HTML or JSON
            content_type = graph_response.headers.get('content-type', '')

            if 'text/html' in content_type:
                print("\n[OK] Graph generated successfully (HTML response)!")
                print(f"Response size: {len(graph_response.text)} bytes")
                print("HTML visualization ready")

                # Save to file
                with open('graph_output.html', 'w', encoding='utf-8') as f:
                    f.write(graph_response.text)
                print("Saved to: graph_output.html")

            elif 'application/json' in content_type:
                graph_result = graph_response.json()
                print("\n[OK] Graph generated successfully (JSON response)!")
                print(f"Response keys: {list(graph_result.keys())}")

                # Display graph spec
                if 'chartType' in graph_result:
                    print(f"\nChart Type: {graph_result.get('chartType')}")
                    print(f"X Field: {graph_result.get('xField')}")
                    print(f"Y Field: {graph_result.get('yField')}")
                    print(f"Allowed Chart Types: {graph_result.get('chartTypes', [])}")

            print("\n" + "=" * 80)
            print("[OK] WORKFLOW COMPLETE!")
            print("=" * 80)
            print(f"\nSummary:")
            print(f"  1. Query executed -> response_id: {response_id}")
            print(f"  2. Graph generated -> content-type: {content_type}")

        else:
            print("\n[FAIL] Graph generation failed!")
            error_text = graph_response.text[:500] if hasattr(graph_response, 'text') else str(graph_response.content[:500])
            print(f"Error: {error_text}")

    else:
        print(f"\n[FAIL] Query execution failed!")
        error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
        print(f"Error: {error_text}")

except Exception as e:
    print(f"\n[ERROR] Exception occurred: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
