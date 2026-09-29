from __future__ import annotations
import os
import requests


def configured() -> bool:
    return bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL") and os.getenv("LLM_MODEL"))


def chat(system: str, user: str, timeout: int = 45) -> str:
    """Call a generic OpenAI-compatible Chat Completions endpoint.

    Set LLM_BASE_URL to the provider's API root ending in /v1 (or equivalent),
    LLM_API_KEY, and LLM_MODEL. If no LLM is configured, the app uses a
    deterministic template and remains fully demoable.
    """
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    url = base + "/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": os.environ["LLM_MODEL"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
