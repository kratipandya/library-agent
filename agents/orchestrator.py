"""Orchestrator: routes each user message to the right specialist agent.

Pattern: agents-as-tools. The orchestrator is itself an SK agent whose tools
are the Content agent (shelf text) and Catalog agent (bibliographic data).
The LLM decides the route per question and may call both for compound
questions; every delegation is printed so routing stays observable (this
becomes App Insights tracing in the cloud).

Usage:
    uv run python -m agents.orchestrator "When was Dracula first published?"
    uv run python -m agents.orchestrator            # interactive chat (multi-turn)
"""

import argparse
import asyncio
import sys
from typing import Annotated

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions import kernel_function

from agents.catalog_agent import build_catalog_agent
from agents.content_agent import build_content_agent
from agents.llm import build_chat_service, get_model_id, invoke_with_retry

INSTRUCTIONS = """\
You are the orchestrator of a library chatbot. You never answer book questions
yourself — you delegate to two specialists and compose their replies:

- ask_content_agent: questions about the TEXT of books on the curated shelf —
  plot, characters, quotes, "what happens", themes. Only works for shelf books.
- ask_catalog_agent: bibliographic questions about ANY book — author,
  publication date, editions, subjects, "what is it about" at catalog level.

Routing rules:
- Route by what the question needs, not by which book it mentions.
- Compound questions (e.g. "who wrote X and how does it end?") → call both
  and merge the answers.
- Pass the specialist a self-contained question: resolve pronouns and context
  from the conversation first ("it" → the book being discussed).
- Greetings/small talk: reply briefly yourself and mention what you can do.
- If the content agent reports a book is not on the shelf, tell the user that
  content questions only work for the curated shelf, and offer catalog info
  instead.
"""


class SpecialistsPlugin:
    """The two specialist agents, exposed to the orchestrator as tools."""

    def __init__(self) -> None:
        self._content_agent = build_content_agent()
        self._catalog_agent = build_catalog_agent()

    @kernel_function(
        description=(
            "Ask the Content specialist about the text of a book on the curated "
            "shelf: plot, characters, quotes, themes. Send a self-contained question."
        )
    )
    async def ask_content_agent(
        self, question: Annotated[str, "self-contained content question"]
    ) -> str:
        print(f'  [route] → ContentAgent: "{question}"')
        response = await invoke_with_retry(
            lambda: self._content_agent.get_response(messages=question)
        )
        return str(response.message.content)

    @kernel_function(
        description=(
            "Ask the Catalog specialist for bibliographic data about any book: "
            "author, publish date, editions, subjects. Send a self-contained question."
        )
    )
    async def ask_catalog_agent(
        self, question: Annotated[str, "self-contained bibliographic question"]
    ) -> str:
        print(f'  [route] → CatalogAgent: "{question}"')
        response = await invoke_with_retry(
            lambda: self._catalog_agent.get_response(messages=question)
        )
        return str(response.message.content)


def build_orchestrator() -> ChatCompletionAgent:
    return ChatCompletionAgent(
        service=build_chat_service("orchestrator"),
        name="Orchestrator",
        instructions=INSTRUCTIONS,
        plugins=[SpecialistsPlugin()],
    )


async def ask_once(orchestrator: ChatCompletionAgent, question: str) -> None:
    response = await invoke_with_retry(lambda: orchestrator.get_response(messages=question))
    print(f"\n{response.message.content}")


async def chat_loop(orchestrator: ChatCompletionAgent) -> None:
    """Multi-turn chat: the thread carries conversation state between turns."""
    thread = ChatHistoryAgentThread()
    print("Library chatbot — ask about books (empty line to quit).")
    while True:
        try:
            question = input("\nyou> ").strip()
        except EOFError:
            break
        if not question:
            break
        # default-arg binding: capture this turn's values, not the loop variables (B023)
        response = await invoke_with_retry(
            lambda q=question, t=thread: orchestrator.get_response(messages=q, thread=t)
        )
        thread = response.thread
        print(f"\nbot> {response.message.content}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Library chatbot orchestrator.")
    parser.add_argument("question", nargs="?", help="one question (omit for interactive chat)")
    args = parser.parse_args()

    print(f"Model: {get_model_id()}")
    orchestrator = build_orchestrator()
    if args.question:
        await ask_once(orchestrator, args.question)
    else:
        await chat_loop(orchestrator)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
