"""SK plugin exposing the Phase 1 FAISS index as tools for the Content agent.

The heavy resources (embedding model, index) load lazily on first use and are
shared across calls — the agent may call search several times per conversation.
"""

import json
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function
from sentence_transformers import SentenceTransformer

from ingestion.vector_store import EMBEDDING_MODEL, QUERY_PREFIX, FaissVectorStore

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = REPO_ROOT / "data" / "index"
SHELF_PATH = REPO_ROOT / "ingestion" / "shelf.json"
TOP_K = 5
CANDIDATES_WHEN_FILTERED = 40  # oversample, then narrow to the requested book


class BookContentPlugin:
    """Tools for answering questions about the curated shelf's actual text."""

    def __init__(self) -> None:
        self._store: FaissVectorStore | None = None
        self._model: SentenceTransformer | None = None

    def _ensure_loaded(self) -> tuple[FaissVectorStore, SentenceTransformer]:
        if self._store is None:
            self._store = FaissVectorStore.load(INDEX_DIR)
        if self._model is None:
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._store, self._model

    @kernel_function(description="List every book on the shelf (title and author).")
    def list_shelf(self) -> str:
        with SHELF_PATH.open() as f:
            books = json.load(f)["books"]
        return "\n".join(f"- {b['title']} by {b['author']}" for b in books)

    @kernel_function(
        description=(
            "Search the full text of the shelf's books and return the most relevant "
            "passages. Phrase the query specifically; include character or book names "
            "when known. Optionally restrict results to one book by title."
        )
    )
    def search_book_content(
        self,
        query: Annotated[str, "specific natural-language search query"],
        book_title: Annotated[str | None, "optional: restrict to this book"] = None,
    ) -> str:
        store, model = self._ensure_loaded()
        print(f'  [tool] search_book_content(query="{query}", book_title={book_title!r})')

        vector = model.encode(QUERY_PREFIX + query, normalize_embeddings=True)
        top_k = CANDIDATES_WHEN_FILTERED if book_title else TOP_K
        results = store.search(vector, top_k=top_k)
        if book_title:
            wanted = book_title.lower()
            results = [r for r in results if wanted in r.record["title"].lower()][:TOP_K]
        if not results:
            return f"No passages found (book_title={book_title!r} may not be on the shelf)."

        passages = [
            f"[{r.record['title']} — chunk {r.record['chunk_index']}, "
            f"score {r.score:.2f}]\n{r.record['text']}"
            for r in results
        ]
        return "\n\n---\n\n".join(passages)
