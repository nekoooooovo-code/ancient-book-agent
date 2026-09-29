from __future__ import annotations

import os
import requests


def _secret(name: str, default: str = "") -> str:
    """Read a secret from environment variables first, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return str(value)

    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def provider() -> str:
    if _secret("OPENAI_API_KEY"):
        return "openai"
    if _secret("LLM_API_KEY") and _secret("LLM_BASE_URL") and _secret("LLM_MODEL"):
        return "openai_compatible"
    return "none"


def model_name() -> str:
    if provider() == "openai":
        return _secret("OPENAI_MODEL", "gpt-6-astra")
    if provider() == "openai_compatible":
        return _secret("LLM_MODEL", "")
    return ""


def configured() -> bool:
    return provider() != "none"


def _openai_responses(system: str, user: str) -> str:
    """Call OpenAI's Responses API with the official Python SDK."""
    from openai import OpenAI

    client = OpenAI(api_key=_secret("OPENAI_API_KEY"))
    response = client.responses.create(
        model=model_name(),
        instructions=system,
        input=user,
    )
    text = getattr(response, "output_text", "")
    if not text:
        raise RuntimeError("OpenAI Responses API returned no output_text.")
    return text


def _compatible_chat_completions(system: str, user: str, timeout: int = 45) -> str:
    """Fallback for other OpenAI-compatible providers."""
    base = _secret("LLM_BASE_URL").rstrip("/")
    url = base + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {_secret('LLM_API_KEY')}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _secret("LLM_MODEL"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def chat(system: str, user: str, timeout: int = 45) -> str:
    p = provider()
    if p == "openai":
        return _openai_responses(system, user)
    if p == "openai_compatible":
        return _compatible_chat_completions(system, user, timeout=timeout)
    raise RuntimeError("No LLM provider is configured.")
