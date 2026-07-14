"""Shared LLM service factory: Semantic Kernel chat service backed by OpenRouter.

OpenRouter speaks the OpenAI-compatible API, so we use SK's standard OpenAI
connector pointed at OpenRouter's base URL. Every agent gets its service from
here — model choice and credentials live in .env, not in code.

Required in .env (see .env.example):
    OPENROUTER_API_KEY=sk-or-v1-...
Optional:
    OPENROUTER_MODEL=some/other-model:free   (defaults to DEFAULT_MODEL)
"""

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# :free variants only — the €7.90 credit is a buffer, not a budget (CLAUDE.md).
# Free-tier capacity is a shared pool and models get saturated upstream; when this
# one 429s persistently, override via OPENROUTER_MODEL in .env rather than editing code.
# Known-good alternative: qwen/qwen3-next-80b-a3b-instruct:free
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


def get_model_id() -> str:
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)


def build_chat_service(service_id: str) -> OpenAIChatCompletion:
    """Create a chat completion service for one agent (service_id names it in SK)."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key "
            "(create one at https://openrouter.ai/keys)."
        )
    # Hard timeout: free-tier requests occasionally hang; fail fast and let
    # invoke_with_retry handle it rather than stalling for openai's 600s default.
    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=90.0)
    return OpenAIChatCompletion(
        service_id=service_id,
        ai_model_id=get_model_id(),
        async_client=client,
    )


RATE_LIMIT_MAX_ATTEMPTS = 4


async def invoke_with_retry[T](operation: Callable[[], Awaitable[T]]) -> T:
    """Run an async LLM call, retrying 429s and honoring the server's Retry-After hint.

    Free-tier models are shared pools: 429 means "the pool is busy right now",
    and OpenRouter includes retry_after_seconds telling us exactly how long to
    wait — guessing with blind exponential backoff undershoots it.
    """
    for attempt in range(1, RATE_LIMIT_MAX_ATTEMPTS + 1):
        try:
            return await operation()
        except Exception as error:
            text = str(error)
            if "429" not in text or attempt == RATE_LIMIT_MAX_ATTEMPTS:
                raise
            hint = re.search(r"retry_after_seconds'?: (\d+)", text)
            wait = int(hint.group(1)) + 1 if hint else 10 * 2 ** (attempt - 1)
            print(f"  [rate-limited] attempt {attempt}/{RATE_LIMIT_MAX_ATTEMPTS}, waiting {wait}s")
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")  # loop always returns or raises
