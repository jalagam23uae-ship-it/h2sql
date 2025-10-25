import yaml
from functools import lru_cache
from typing import Dict
import os
from pathlib import Path

from llm_config.llm_config_model import LlmConfig, PipelineTask

# --- Global storage ---
LLM_CONFIGS: Dict[str, LlmConfig] = {}
TASK_TO_LLM: Dict[str, str] = {}

# Default config path (relative to app directory)
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm_config.yml")

@lru_cache(maxsize=1)
def load_llm_config(path: str = None):
    global LLM_CONFIGS, TASK_TO_LLM

    if path is None:
        path = DEFAULT_CONFIG_PATH

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    # Parse llms
    llm_list = data.get("llms", {})
    LLM_CONFIGS = {name: LlmConfig(**cfg) for name, cfg in llm_list.items()}

    # Parse pipelines
    pipelines_raw = data.get("pipelines", [])
    TASK_TO_LLM = {
        task["name"]: task["llm"]
        for task in pipelines_raw
    }

def get_llm_config(task_name: str) -> LlmConfig:
    if not TASK_TO_LLM:
        load_llm_config()

    if task_name not in TASK_TO_LLM:
        raise KeyError(f"Task '{task_name}' not found in pipelines")

    llm_key = TASK_TO_LLM[task_name]
    if llm_key not in LLM_CONFIGS:
        raise KeyError(f"LLM '{llm_key}' referenced by task '{task_name}' not found in llms config")

    return LLM_CONFIGS[llm_key]

def get_llm_config_list() -> Dict[str, LlmConfig]:
    if not TASK_TO_LLM:
        load_llm_config()

    return LLM_CONFIGS

def get_task_config(path: str = None) -> dict | None:
    if path is None:
        path = DEFAULT_CONFIG_PATH

    with open(path, "r") as f:
        data = yaml.safe_load(f)
    mapping = {}
    for pipe in data["pipelines"]:
            name = pipe.get("name")
            llm_key = pipe["llm"]
            mapping[name] = data["llms"].get(llm_key)
    return mapping

def get_task_llm_config(task_name: str, path: str = None) -> dict:
    if path is None:
        path = DEFAULT_CONFIG_PATH

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    for pipe in data["pipelines"]:
            name = pipe.get("name")
            llm_key = pipe["llm"]
            if name == task_name:
                return data["llms"].get(llm_key)
