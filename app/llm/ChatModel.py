import json
import os
import requests
from litellm import completion
from pydantic import BaseModel


# ✅ Configuration
MODEL_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # e.g. ollama, openai, huggingface
MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "Llama-4-Scout-17B-16E-Instruct")
MODEL_API_URL = os.getenv("CHAT_MODEL_API_URL", "http://192.168.1.6:3034/v1")
API_KEY = os.getenv("LLM_API_KEY", "llm")


class ChatModel:
    """
    Universal wrapper for LiteLLM + raw HTTP fallback.
    """

    def __init__(self, api_url: str = None, model: str = None, api_key: str = None):
        self.api_url = api_url or MODEL_API_URL
        self.model = model or f"{MODEL_PROVIDER}/{MODEL_NAME}"  # ✅ e.g. "ollama/Llama-4-Scout-17B-16E-Instruct"
        self.api_key = api_key or API_KEY

    # ------------------------------------------------------------------
    # Primary LiteLLM call
    # ------------------------------------------------------------------
    def infer_llm(
            self,
            user_prompt: str,
            system_prompt: str = "",
            temperature: float = 0.1,
            response_format: BaseModel = None,
    ) -> str:
        """Run LLM inference using LiteLLM first, fallback to raw HTTP."""
        messages = (
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            if system_prompt
            else [{"role": "user", "content": user_prompt}]
        )

        print("\n[ChatModel] Sending payload:")
        print(
            json.dumps(
                {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        # ----------------------------
        # Try LiteLLM
        # ----------------------------
        try:
            response = completion(
                model=self.model,
                messages=messages,
                api_base=self.api_url,
                api_key=self.api_key,
                temperature=temperature,
            )
            return response["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"\n[ChatModel] LiteLLM failed: {e}")
            print("Retrying via raw HTTP request...")

            # ----------------------------
            # Raw HTTP Fallback
            # ----------------------------
            try:
                # Extract model name without provider prefix for direct API calls
                model_name = self.model.split('/')[-1] if '/' in self.model else self.model

                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }

                print("\n[ChatModel] Fallback payload:")
                print(json.dumps(payload, indent=2, ensure_ascii=False))

                headers = {"Content-Type": "application/json"}
                if self.api_key and self.api_key != "llm":
                    headers["Authorization"] = f"Bearer {self.api_key}"

                resp = requests.post(
                    f"{self.api_url}/chat/completions",
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=300,  # Increased from 90 to 300 seconds for large prompts
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                print(f"[ChatModel] Error {resp.status_code}: {resp.text}")
                return f"Error: {resp.status_code}"

            except Exception as e2:
                print(f"[ChatModel] Fallback failed: {e2}")
                return f"Error during inference: {e2}"

    # ------------------------------------------------------------------
    # Backward-compatible helper (legacy API)
    # ------------------------------------------------------------------
    def chat_with_model(self, system_prompt: str, user_prompt: str, temperature: float = 0.1):
        """Legacy alias for older scripts using chat_with_model()."""
        return self.infer_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )


# ----------------------------------------------------------------------
# Manual test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("\n=== TESTING LLM ===\n")

    chat_model = ChatModel()

    system_prompt = "You are an expert data documentation assistant."
    user_prompt = "Write a 2-line description of a customer database table."

    response = chat_model.chat_with_model(system_prompt, user_prompt)

    print("\nModel Response:\n", response)
