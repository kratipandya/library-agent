"""Smoke test: can Semantic Kernel reach an LLM through OpenRouter at all?

No agents, no tools — one chat round-trip. Run this after setting up .env.
Retries on rate limits (free-tier models are shared and 429s are normal).

Usage:
    uv run python agents/smoke_test.py
"""

import asyncio
import sys
import time

from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

from agents.llm import build_chat_service, get_model_id

MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 5


async def main() -> int:
    service = build_chat_service(service_id="smoke-test")
    print(f"Model: {get_model_id()}")

    history = ChatHistory()
    history.add_system_message("You are the test probe of a library chatbot backend.")
    history.add_user_message("Reply with exactly: The library is open.")
    settings = OpenAIChatPromptExecutionSettings(max_tokens=1000)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reply = await service.get_chat_message_content(
                chat_history=history, settings=settings
            )
            print(f"Reply: {reply}")
            print("Smoke test PASSED — Semantic Kernel ↔ OpenRouter round-trip works.")
            return 0
        except Exception as error:  # noqa: BLE001 — a smoke test reports, never crashes
            if "429" in str(error) and attempt < MAX_ATTEMPTS:
                wait = BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
                print(f"Rate limited (attempt {attempt}/{MAX_ATTEMPTS}) — waiting {wait}s ...")
                time.sleep(wait)
                continue
            print(f"Smoke test FAILED: {error}")
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
