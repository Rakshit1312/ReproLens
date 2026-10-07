from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class OllamaService:
    def __init__(self, endpoint: str | None = None, model: str | None = None):
        self.endpoint = (endpoint or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "codellama:7b-instruct")

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode()
        req = urllib.request.Request(
            self.endpoint + "/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode())
        return str(data.get("response", ""))


def grounded_prompt(question: str, risk: dict[str, Any], contexts: list[dict[str, Any]]) -> str:
    evidence = "\n\n".join(
        f"SOURCE: {c['source']}\n{c['text']}" for c in contexts
    ) or "No repository evidence was retrieved."
    return f"""You are ReproLens, an AI-assisted DevOps analysis system.
Answer only from the supplied evidence and structured risk data. If evidence is insufficient, say so.
Do not invent files, versions, failures, or historical cases.

QUESTION:
{question}

STRUCTURED RISK DATA:
{json.dumps(risk, indent=2)}

RETRIEVED EVIDENCE:
{evidence}

Return:
1. Risk interpretation
2. Evidence supporting it
3. Uncertainty/limitations
4. Recommended verification step
"""
