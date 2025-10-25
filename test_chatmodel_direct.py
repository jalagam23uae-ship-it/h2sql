"""
Test ChatModel directly with OpenRouter credentials
"""
import sys
sys.path.append("D:\\h2sql\\app")

from llm.ChatModel import ChatModel

print("=" * 80)
print("CHATMODEL DIRECT TEST")
print("=" * 80)

API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/meta-llama/llama-4-scout"

print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
print(f"Base URL: {BASE_URL}")
print(f"Model: {MODEL}")
print("=" * 80)

chat_model = ChatModel(
    api_url=BASE_URL,
    model=MODEL,
    api_key=API_KEY
)

print("\n[TEST] Simple Question")
print("-" * 80)

response = chat_model.infer_llm(
    user_prompt="Say 'Hello from ChatModel' and nothing else.",
    temperature=0.2
)

print(f"\n[RESPONSE]: {response}")
print("\n" + "=" * 80)
