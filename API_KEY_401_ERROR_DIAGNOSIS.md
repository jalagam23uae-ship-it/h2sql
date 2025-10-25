# API Key 401 Error - Diagnosis and Solution

## Problem Summary

Despite updating the API key in `llm_config.yml` to the new OpenRouter key:
```yaml
api_key: "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"
```

The H2SQL server still returns 401 authentication errors when trying to generate SQL.

## Root Cause Analysis

### What Works ✅
1. **Direct API Test** - The new API key works perfectly when tested directly:
   ```python
   # test_openrouter_direct.py - SUCCESS
   response = requests.post(
       "https://openrouter.ai/api/v1/chat/completions",
       headers={"Authorization": f"Bearer {API_KEY}"},
       json={"model": "meta-llama/llama-4-scout", ...}
   )
   # Returns 200 OK with "Hello, World!"
   ```

2. **ChatModel Direct Test** - ChatModel class works when called directly:
   ```python
   # test_chatmodel_direct.py - SUCCESS
   chat_model = ChatModel(
       api_url="https://openrouter.ai/api/v1",
       model="openai/meta-llama/llama-4-scout",
       api_key="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"
   )
   response = chat_model.infer_llm("Say hello")
   # Returns "Hello from ChatModel"
   ```

### What Fails ❌
**H2SQL Server Endpoints** - All `/executequey` requests fail with 401:
```
Failed to generate SQL from question: LLM returned invalid response: Error: 401
```

## Diagnosis

The issue is in how LiteLLM is being configured in the server context vs. direct tests.

### In ChatModel.py (line 63-70):
```python
try:
    response = completion(
        model=self.model,  # "openai/meta-llama/llama-4-scout"
        messages=messages,
        api_base=self.api_url,  # "https://openrouter.ai/api/v1"
        api_key=self.api_key,  # "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"
        temperature=temperature,
    )
    return response["choices"][0]["message"]["content"]
except Exception as e:
    # Fallback to HTTP...
```

**The Problem**: LiteLLM sees `model="openai/meta-llama/llama-4-scout"` and may be:
1. Trying to use OpenAI's API instead of OpenRouter
2. Not recognizing "openai" as a valid provider prefix for OpenRouter
3. Using the wrong authentication method

### Why Direct Test Works:
The direct HTTP request bypasses LiteLLM entirely and uses the correct model name:
```python
payload = {
    "model": "meta-llama/llama-4-scout",  # NO "openai/" prefix
    ...
}
```

## Solutions

### Solution 1: Change Provider Prefix in llm_config.yml

**Current**:
```yaml
llms:
  default:
    provider: openai  # ← This is the problem
    base_url: "https://openrouter.ai/api/v1"
    model: "meta-llama/llama-4-scout"
```

**Fixed**:
```yaml
llms:
  default:
    provider: openrouter  # ← Change to "openrouter"
    base_url: "https://openrouter.ai/api/v1"
    model: "meta-llama/llama-4-scout"
```

This will make ChatModel construct the model string as `"openrouter/meta-llama/llama-4-scout"` which LiteLLM should recognize.

### Solution 2: Use Environment Variable Override

Add to ChatModel initialization in data_upload_api.py:
```python
import os
os.environ["OPENROUTER_API_KEY"] = llm_config.api_key

chat_model = ChatModel(
    api_url=llm_config.base_url,
    model=f"openrouter/{llm_config.model}",  # Force "openrouter/" prefix
    api_key=llm_config.api_key
)
```

### Solution 3: Force HTTP Fallback (Bypass LiteLLM)

Modify ChatModel.py to skip LiteLLM for OpenRouter:

```python
def infer_llm(self, user_prompt, system_prompt="", temperature=0.1):
    messages = [...]

    # Check if using OpenRouter
    if "openrouter.ai" in self.api_url:
        # Skip LiteLLM, use HTTP directly
        return self._http_fallback(messages, temperature)

    # Otherwise try LiteLLM first
    try:
        response = completion(...)
    except Exception as e:
        return self._http_fallback(messages, temperature)

def _http_fallback(self, messages, temperature):
    # Extract model name
    model_name = self.model.split('/')[-1] if '/' in self.model else self.model

    payload = {"model": model_name, "messages": messages, ...}
    headers = {"Content-Type": "application/json"}
    if self.api_key and self.api_key != "llm":
        headers["Authorization"] = f"Bearer {self.api_key}"

    resp = requests.post(f"{self.api_url}/chat/completions", ...)
    return resp.json()["choices"][0]["message"]["content"]
```

## Recommended Action

**Try Solution 1 first** (simplest):

1. Edit `D:\h2sql\app\llm_config.yml`:
   ```yaml
   llms:
     default:
       provider: openrouter  # Change from "openai"
       base_url: "https://openrouter.ai/api/v1"
       api_key: "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"
       model: "meta-llama/llama-4-scout"
       temperature: 0.2
   ```

2. Restart the server:
   ```bash
   taskkill /F /IM python.exe
   cd D:\h2sql\app
   python main.py
   ```

3. Test again:
   ```bash
   python D:\h2sql\test_simple_query.py
   ```

## Verification

After applying the fix, you should see:
- ✅ Status: 200
- ✅ Generated SQL query
- ✅ Database results

If it still fails, check the server logs for:
```
[ChatModel] LiteLLM failed: <error message>
```

This will tell us exactly what LiteLLM is complaining about.

## Alternative: Use Local LLM

If OpenRouter continues to fail, fall back to the local LLM that was working before:

```yaml
llms:
  default:
    provider: openai
    base_url: "http://192.168.1.7:11434/v1"
    model: "llama4:16x17b"
    temperature: 0.2
```

---

**Status**: Awaiting fix implementation (Solution 1 recommended)
**Priority**: HIGH - Blocks all testing
**Estimated Time**: 2 minutes to apply + restart
