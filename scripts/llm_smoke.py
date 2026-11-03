"""One-call smoke test for the configured LLM endpoint. Never prints the API key.

Run: .venv/Scripts/python.exe -m scripts.llm_smoke
"""

from __future__ import annotations

import sys
import time

import httpx

from app.llm import load_llm_config


def main() -> int:
    cfg = load_llm_config()
    if "PASTE" in cfg.api_key:
        print("LLM_API_KEY in .env is still the placeholder. Paste your key first.")
        return 1

    payload: dict[str, object] = {
        "model": cfg.model,
        "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
    }
    if cfg.reasoning_effort:
        payload["reasoning_effort"] = cfg.reasoning_effort

    print(f"POST {cfg.chat_completions_url} model={cfg.model} effort={cfg.reasoning_effort or 'default'}")
    start = time.monotonic()
    response = httpx.post(
        cfg.chat_completions_url,
        headers={"Authorization": f"Bearer {cfg.api_key}"},
        json=payload,
        timeout=cfg.timeout_seconds,
    )
    elapsed = time.monotonic() - start
    print(f"HTTP {response.status_code} in {elapsed:.1f}s")
    if response.status_code != 200:
        print(response.text[:500])
        return 1

    message = response.json()["choices"][0]["message"]
    print(f"content: {message.get('content')!r}")
    print(f"reasoning_content present: {bool(message.get('reasoning_content'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
