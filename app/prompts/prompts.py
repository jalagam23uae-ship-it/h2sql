import json
from pathlib import Path

class Prompts:
    def __init__(self) -> None:
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        prompts_path = Path(__file__).resolve().parents[1] / 'prompts' / 'prompts.json'
        if not prompts_path.is_file():
            raise FileNotFoundError(f"Prompts file not found: {prompts_path}")
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing prompts.json: {e}")

    def get_prompt_by_key(self, key: str) -> str:
        prompt = self.prompts.get(key, {}).get('prompt')
        return prompt