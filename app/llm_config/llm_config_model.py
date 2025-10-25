from pydantic import BaseModel

class LlmConfig(BaseModel):
    provider: str
    base_url: str
    model: str
    temperature: float

class PipelineTask(BaseModel):
    name: str
    llm: str  # This refers to an LLM key in llms