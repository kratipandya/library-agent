"""Chunk cleaned books into paragraph-aware pieces sized for the embedding model.

Token counts use the embedding model's own tokenizer (bge-small-en-v1.5,
512-token input limit) so no chunk can be silently truncated at embed time.
Chunks target MAX_TOKENS; consecutive chunks share ~OVERLAP_TOKENS of trailing
paragraphs so text near a boundary stays searchable with its context. Worst
case a chunk reaches MAX_TOKENS + OVERLAP_TOKENS = 460, still under the limit.

Output: data/chunks.jsonl — one JSON object per chunk with book metadata.

Usage:
    uv run python ingestion/chunk.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
MAX_TOKENS = 400
OVERLAP_TOKENS = 60

REPO_ROOT = Path(__file__).resolve().parent.parent
SHELF_PATH = REPO_ROOT / "ingestion" / "shelf.json"
CLEAN_DIR = REPO_ROOT / "data" / "clean"
CHUNKS_PATH = REPO_ROOT / "data" / "chunks.jsonl"


def load_shelf_by_id() -> dict[int, dict[str, Any]]:
    with SHELF_PATH.open() as f:
        return {book["id"]: book for book in json.load(f)["books"]}


def token_len(tokenizer: Any, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def split_long_paragraph(tokenizer: Any, paragraph: str) -> list[str]:
    """Split an over-long paragraph on sentence boundaries.

    A single sentence longer than MAX_TOKENS (rare: tables, lists) is
    hard-split on token windows as a last resort.
    """
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and token_len(tokenizer, candidate) > MAX_TOKENS:
            parts.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        parts.append(current)

    result: list[str] = []
    for part in parts:
        ids = tokenizer.encode(part, add_special_tokens=False)
        if len(ids) <= MAX_TOKENS:
            result.append(part)
        else:
            for i in range(0, len(ids), MAX_TOKENS):
                result.append(tokenizer.decode(ids[i : i + MAX_TOKENS]))
    return result


def chunk_text(tokenizer: Any, text: str) -> list[str]:
    """Pack paragraphs into chunks of at most MAX_TOKENS (+ overlap seed)."""
    paragraphs: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = re.sub(r"\s+", " ", para).strip()  # flatten hard-wrapped lines
        if not para:
            continue
        if token_len(tokenizer, para) > MAX_TOKENS:
            paragraphs.extend(split_long_paragraph(tokenizer, para))
        else:
            paragraphs.append(para)

    chunks: list[str] = []
    current: list[tuple[str, int]] = []  # (paragraph, token_count)
    current_tokens = 0
    for para in paragraphs:
        n_tokens = token_len(tokenizer, para)
        if current and current_tokens + n_tokens > MAX_TOKENS:
            chunks.append("\n\n".join(p for p, _ in current))
            # seed the next chunk with trailing paragraphs as overlap
            overlap: list[tuple[str, int]] = []
            overlap_tokens = 0
            for prev, prev_tokens in reversed(current):
                if overlap_tokens + prev_tokens > OVERLAP_TOKENS:
                    break
                overlap.insert(0, (prev, prev_tokens))
                overlap_tokens += prev_tokens
            current = overlap
            current_tokens = overlap_tokens
        current.append((para, n_tokens))
        current_tokens += n_tokens
    if current:
        chunks.append("\n\n".join(p for p, _ in current))
    return chunks


def main() -> int:
    clean_files = sorted(CLEAN_DIR.glob("*.txt"))
    if not clean_files:
        print(f"No files in {CLEAN_DIR} — run ingestion/clean.py first.")
        return 1

    shelf = load_shelf_by_id()
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)

    total_chunks = 0
    with CHUNKS_PATH.open("w", encoding="utf-8") as out:
        for path in clean_files:
            book_id = int(path.name.split("_", 1)[0])
            book = shelf[book_id]
            chunks = chunk_text(tokenizer, path.read_text(encoding="utf-8"))
            for index, chunk in enumerate(chunks):
                record = {
                    "chunk_id": f"{book_id}-{index:04d}",
                    "book_id": book_id,
                    "title": book["title"],
                    "author": book["author"],
                    "chunk_index": index,
                    "token_count": token_len(tokenizer, chunk),
                    "text": chunk,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_chunks += len(chunks)
            print(f"  {book['title']:<50} {len(chunks):>5} chunks")

    print(f"Done: {total_chunks} chunks from {len(clean_files)} books → {CHUNKS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
