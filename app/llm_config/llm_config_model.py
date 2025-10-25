from pydantic import BaseModel
from typing import Optional

class LlmConfig(BaseModel):
    provider: str
    base_url: str
    model: str
    temperature: float
    api_key: Optional[str] = None

class PipelineTask(BaseModel):
    name: str
    llm: str  # This refers to an LLM key in llms