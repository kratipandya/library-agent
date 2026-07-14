"""Content agent: answers questions about the shelf's books, grounded in the index.

This is query.py grown up — instead of printing raw chunks, an LLM decides
what to search for (possibly rephrasing or filtering by book), reads the
retrieved passages, and writes a cited answer.

Usage:
    uv run python -m agents.content_agent "How does the monster learn language?"
"""

import argparse
import asyncio
import sys

from semantic_kernel.agents import ChatCompletionAgent

from agents.content_plugin import BookContentPlugin
from agents.llm import build_chat_service, get_model_id, invoke_with_retry

INSTRUCTIONS = """\
You are the Content agent of a library chatbot. You answer questions about the
actual text of the books on a curated shelf — nothing else.

Rules:
- Ground every answer in search_book_content results. Never answer from memory,
  even for famous books: your copy of the text is the only source of truth.
- Phrase search queries specifically. If the user's question is vague, rewrite
  it with character/book names from context before searching. When you know
  which book is meant, pass book_title to narrow the search.
- Cite passages inline as (Title, chunk N).
- If the question concerns a book that is not on the shelf (use list_shelf to
  check when unsure), say so plainly instead of guessing.
- Be concise: answer first, then supporting citations.
"""


def build_content_agent() -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=build_chat_service("content-agent"),
        name="ContentAgent",
        instructions=INSTRUCTIONS,
        plugins=[BookContentPlugin()],
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the Content agent about shelf books.")
    parser.add_argument("question", help="a question about a book's content")
    args = parser.parse_args()

    print(f"Model: {get_model_id()}")
    agent = build_content_agent()
    response = await invoke_with_retry(lambda: agent.get_response(messages=args.question))
    print(f"\n{response.message.content}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
