"""SK plugin exposing the Open Library API as tools for the Catalog agent.

Open Library (openlibrary.org) is free and keyless. Etiquette per their docs:
identify yourself via User-Agent. Both tools return compact plain text —
the LLM reads it, so formatting beats completeness.
"""

from typing import Annotated

import requests
from semantic_kernel.functions import kernel_function

SEARCH_URL = "https://openlibrary.org/search.json"
WORK_URL = "https://openlibrary.org/works/{work_id}.json"
HEADERS = {"User-Agent": "library-agent portfolio project (github.com/kratipandya/library-agent)"}
TIMEOUT_SECONDS = 30
SEARCH_FIELDS = "key,title,author_name,first_publish_year,edition_count"
MAX_RESULTS = 5
MAX_SUBJECTS = 12


class OpenLibraryPlugin:
    """Tools for finding books and their bibliographic details."""

    @kernel_function(
        description=(
            "Search the Open Library catalog by title/author keywords. Returns up to "
            "5 matches with their work key (needed for get_book_details), author, "
            "first publish year, and edition count."
        )
    )
    def search_catalog(
        self, query: Annotated[str, "title and/or author keywords"]
    ) -> str:
        print(f'  [tool] search_catalog(query="{query}")')
        resp = requests.get(
            SEARCH_URL,
            params={"q": query, "limit": MAX_RESULTS, "fields": SEARCH_FIELDS},
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        docs = resp.json()["docs"]
        if not docs:
            return f"No catalog matches for {query!r}."

        lines = []
        for doc in docs:
            authors = ", ".join(doc.get("author_name", ["unknown author"]))
            lines.append(
                f"- {doc.get('title', 'untitled')} by {authors} "
                f"(first published {doc.get('first_publish_year', '?')}, "
                f"{doc.get('edition_count', '?')} editions, work_key={doc['key']})"
            )
        return "\n".join(lines)

    @kernel_function(
        description=(
            "Get details for one book: description and subjects. Requires a work_key "
            "from search_catalog, e.g. '/works/OL893415W'."
        )
    )
    def get_book_details(
        self, work_key: Annotated[str, "Open Library work key, e.g. /works/OL893415W"]
    ) -> str:
        print(f'  [tool] get_book_details(work_key="{work_key}")')
        work_id = work_key.strip("/").removeprefix("works/")
        resp = requests.get(
            WORK_URL.format(work_id=work_id), headers=HEADERS, timeout=TIMEOUT_SECONDS
        )
        if resp.status_code == 404:
            return f"No work found for key {work_key!r} — use a key from search_catalog."
        resp.raise_for_status()
        work = resp.json()

        # description is either a plain string or {"type": ..., "value": ...}
        description = work.get("description", "no description available")
        if isinstance(description, dict):
            description = description.get("value", "no description available")

        subjects = ", ".join(work.get("subjects", [])[:MAX_SUBJECTS]) or "none listed"
        return (
            f"Title: {work.get('title', 'untitled')}\n"
            f"Subjects: {subjects}\n"
            f"Description: {description}"
        )
