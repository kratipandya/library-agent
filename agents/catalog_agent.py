"""Catalog agent: answers bibliographic questions about any book via Open Library.

The counterpart to the Content agent: this one knows metadata (authors, dates,
editions, subjects) for the whole catalog, but nothing about what's inside
the books.

Usage:
    uv run python -m agents.catalog_agent "When was Dune first published?"
"""

import argparse
import asyncio
import sys

from semantic_kernel.agents import ChatCompletionAgent

from agents.catalog_plugin import OpenLibraryPlugin
from agents.llm import build_chat_service, get_model_id, invoke_with_retry

INSTRUCTIONS = """\
You are the Catalog agent of a library chatbot. You answer bibliographic
questions about any book: authors, publication dates, editions, subjects,
and what a book is about.

Rules:
- Always look books up with search_catalog; use get_book_details (with the
  work_key from search results) when the question needs description or
  subjects. Never answer from memory — the catalog is the source of truth.
- If several matches could fit, prefer the one with the most editions unless
  the user's wording says otherwise, and mention the ambiguity briefly.
- You do not know the text inside books. If asked about plot events, quotes,
  or "what happens", say that content questions are outside your catalog role.
- Be concise: answer first, then relevant extras (editions, subjects).
"""


def build_catalog_agent() -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=build_chat_service("catalog-agent"),
        name="CatalogAgent",
        instructions=INSTRUCTIONS,
        plugins=[OpenLibraryPlugin()],
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the Catalog agent about any book.")
    parser.add_argument("question", help="a bibliographic question")
    args = parser.parse_args()

    print(f"Model: {get_model_id()}")
    agent = build_catalog_agent()
    response = await invoke_with_retry(lambda: agent.get_response(messages=args.question))
    print(f"\n{response.message.content}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
