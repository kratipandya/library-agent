"""Embed all chunks and build the local FAISS index.

Encodes data/chunks.jsonl with bge-small-en-v1.5 (downloads ~130MB on first
run) and saves the index + records to data/index/. Vectors are normalized so
inner-product search equals cosine similarity.

Usage:
    uv run python ingestion/embed.py
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from vector_store import EMBEDDING_MODEL, FaissVectorStore

REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = REPO_ROOT / "data" / "chunks.jsonl"
INDEX_DIR = REPO_ROOT / "data" / "index"
BATCH_SIZE = 64


def load_chunks() -> list[dict[str, Any]]:
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main() -> int:
    if not CHUNKS_PATH.exists():
        print(f"{CHUNKS_PATH} missing — run ingestion/chunk.py first.")
        return 1

    chunks = load_chunks()
    print(f"Embedding {len(chunks)} chunks with {EMBEDDING_MODEL} ...")

    model = SentenceTransformer(EMBEDDING_MODEL)
    started = time.perf_counter()
    vectors = model.encode(
        [chunk["text"] for chunk in chunks],
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,  # unit length → inner product == cosine
        show_progress_bar=True,
    )
    elapsed = time.perf_counter() - started
    print(f"Encoded in {elapsed:.0f}s ({len(chunks) / elapsed:.0f} chunks/s)")

    store = FaissVectorStore()
    store.upsert(chunks, vectors)
    store.save(INDEX_DIR)
    print(f"Done: {len(store)} vectors saved → {INDEX_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
