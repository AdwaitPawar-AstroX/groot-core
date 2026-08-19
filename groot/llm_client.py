"""LLM routing layer: local Qwen3 (Ollama) by default, Claude on escalation.

This is the one place that decides "local or Claude" — nothing else in the
codebase should call Ollama or Anthropic directly.
"""

import requests
from pathlib import Path
from .config_loader import get_config

# Anthropic SDK is imported lazily — only needed if we actually escalate,
# so the core loop works even before an API key is configured.


def _load_system_prompt() -> str:
    cfg = get_config()
    prompt_path = Path(__file__).parent.parent / cfg["paths"]["system_prompt"]
    if prompt_path.exists():
        return prompt_path.read_text()
    return "You are Groot, a terse and helpful personal assistant."


SYSTEM_PROMPT = _load_system_prompt()


def _call_ollama(user_text: str, conversation: list[dict]) -> dict:
    cfg = get_config()["llm"]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation + [
        {"role": "user", "content": user_text}
    ]
    resp = requests.post(
        f"{cfg['ollama_url']}/api/chat",
        json={
            "model": cfg["local_model"],
            "messages": messages,
            "stream": False,
            "think": cfg.get("think", False),
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["message"]["content"],
        "source": "local",
    }


def _call_claude(user_text: str, conversation: list[dict], hard: bool = False) -> dict:
    import anthropic  # lazy import

    cfg = get_config()["llm"]["fallback"]
    model = cfg["escalate_model"] if hard else cfg["model"]
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    messages = conversation + [{"role": "user", "content": user_text}]
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return {"text": text, "source": f"claude:{model}"}


def _needs_escalation(local_result: dict, user_text: str) -> bool:
    """Very simple first-pass router — refine this as Groot grows.

    Escalates when the local model:
    - explicitly says it doesn't know / can't do something
    - the reply is suspiciously short for a non-trivial question
    - the user asked something that smells like multi-step reasoning
    """
    text = local_result["text"].lower()
    uncertain_markers = ["i don't know", "i'm not sure", "i cannot", "unable to"]
    if any(m in text for m in uncertain_markers):
        return True
    if len(user_text.split()) > 25 and len(text.split()) < 8:
        return True
    return False


def get_response(user_text: str, conversation: list[dict] | None = None) -> dict:
    """Main entry point. Returns {"text": ..., "source": "local"|"claude:<model>"}."""
    conversation = conversation or []

    try:
        local_result = _call_ollama(user_text, conversation)
    except (requests.exceptions.RequestException, KeyError) as e:
        # Local model unreachable/broken — escalate immediately
        return _call_claude(user_text, conversation, hard=False)

    if _needs_escalation(local_result, user_text):
        return _call_claude(user_text, conversation, hard=False)

    return local_result
