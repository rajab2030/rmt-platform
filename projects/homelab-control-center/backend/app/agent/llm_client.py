"""RMT-CAP-05 (5B) -- minimal local-Ollama client (stdlib only).

Same shape as `experiments/mcr3/atlas.py::LLMClient`. No new dependency, no
streaming. `generate()` returns the raw model text or raises (the caller maps
any exception to a fail-closed `llm_error`).
"""
import json
import urllib.request

from app.agent import loop_config


class LlmClient:
    def __init__(self, model=None, host=None, timeout=None):
        self.model = model or loop_config.AGENT_LLM_MODEL
        self.host = host or loop_config.AGENT_LLM_HOST
        self.timeout = timeout or loop_config.AGENT_LLM_TIMEOUT_SECONDS

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": loop_config.AGENT_LLM_MAX_TOKENS,
                    "temperature": loop_config.AGENT_LLM_TEMPERATURE,
                },
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r).get("response", "").strip()
