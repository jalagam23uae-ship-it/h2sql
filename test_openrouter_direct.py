"""
Direct test of OpenRouter API to diagnose 401 errors
"""
import requests
import json

API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "meta-llama/llama-4-scout"

print("=" * 80)
print("OPENROUTER API DIRECT TEST")
print("=" * 80)
print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
print(f"Base URL: {BASE_URL}")
print(f"Model: {MODEL}")
print("=" * 80)

# Test 1: Simple completion
print("\n[TEST 1] Simple Completion Request")
print("-" * 80)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
    ],
    "temperature": 0.2
}

print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n[SUCCESS] Response:")
        print(json.dumps(result, indent=2))

        if 'choices' in result and len(result['choices']) > 0:
            message = result['choices'][0]['message']['content']
            print(f"\n[RESPONSE TEXT]: {message}")
    else:
        print(f"\n[FAIL] Status {response.status_code}")
        print(f"Response: {response.text}")

        # Try to parse error
        try:
            error_data = response.json()
            print(f"\nError Details:")
            print(json.dumps(error_data, indent=2))
        except:
            print(f"Raw Response: {response.text[:500]}")

except Exception as e:
    print(f"\n[ERROR] Exception occurred: {type(e).__name__}")
    print(f"Message: {str(e)}")

# Test 2: Check if it's a model availability issue
print("\n\n[TEST 2] Try Different Model")
print("-" * 80)

alternative_models = [
    "meta-llama/llama-3.1-8b-instruct",
    "openai/gpt-3.5-turbo",
    "anthropic/claude-instant-1"
]

for alt_model in alternative_models:
    print(f"\nTrying model: {alt_model}")
    payload['model'] = alt_model

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            print(f"  [SUCCESS] {alt_model} works!")
            break
        elif response.status_code == 401:
            print(f"  [401] Authentication error")
        elif response.status_code == 404:
            print(f"  [404] Model not found")
        else:
            print(f"  [ERROR] {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"  [EXCEPTION] {str(e)[:100]}")

# Test 3: Check API key format
print("\n\n[TEST 3] API Key Validation")
print("-" * 80)

print(f"Key starts with 'sk-or-v1-': {API_KEY.startswith('sk-or-v1-')}")
print(f"Key length: {len(API_KEY)}")
print(f"Expected length: 71+ characters")

if not API_KEY.startswith('sk-or-v1-'):
    print("[WARNING] API key format looks incorrect")
    print("Expected format: sk-or-v1-xxxxxxxxxxxxxxxx...")

# Test 4: Try models endpoint
print("\n\n[TEST 4] List Available Models")
print("-" * 80)

try:
    response = requests.get(
        f"{BASE_URL}/models",
        headers=headers,
        timeout=10
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        models_data = response.json()
        print(f"Found {len(models_data.get('data', []))} models")

        # Check if llama-4-scout is available
        available = False
        for model in models_data.get('data', []):
            if 'llama-4-scout' in model.get('id', '').lower():
                print(f"  [FOUND] {model.get('id')}")
                available = True

        if not available:
            print(f"  [NOT FOUND] meta-llama/llama-4-scout not in available models")
            print(f"  Showing first 10 available models:")
            for i, model in enumerate(models_data.get('data', [])[:10], 1):
                print(f"    {i}. {model.get('id')}")
    else:
        print(f"Failed to list models: {response.status_code}")
        print(response.text[:200])

except Exception as e:
    print(f"Exception: {str(e)}")

print("\n" + "=" * 80)
print("END OF DIAGNOSTIC TEST")
print("=" * 80)
