"""Ask the bookshelf a question — the Phase 1 proof.

Embeds the question (with the BGE query prefix), searches the FAISS index,
and prints the best-matching chunks. This is exactly what the Content agent
will do in Phase 2, minus the LLM writing a final answer.

Usage:
    uv run python ingestion/query.py "How does the monster learn to speak?"
    uv run python ingestion/query.py --top-k 3 "What does Sun Tzu say about spies?"
"""

import argparse
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
from vector_store import EMBEDDING_MODEL, QUERY_PREFIX, FaissVectorStore

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = REPO_ROOT / "data" / "index"
SNIPPET_CHARS = 300


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic search over the bookshelf.")
    parser.add_argument("question", help="natural-language question about a shelf book")
    parser.add_argument("--top-k", type=int, default=5, help="number of results (default 5)")
    args = parser.parse_args()

    if not INDEX_DIR.exists():
        print(f"{INDEX_DIR} missing — run ingestion/embed.py first.")
        return 1

    store = FaissVectorStore.load(INDEX_DIR)
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_vector = model.encode(QUERY_PREFIX + args.question, normalize_embeddings=True)

    print(f'Question: "{args.question}"  (searching {len(store)} chunks)\n')
    for rank, result in enumerate(store.search(query_vector, top_k=args.top_k), start=1):
        record = result.record
        snippet = record["text"][:SNIPPET_CHARS].replace("\n", " ")
        print(f"#{rank}  [{result.score:.3f}]  {record['title']} — chunk {record['chunk_index']}")
        print(f"    {snippet}...\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
