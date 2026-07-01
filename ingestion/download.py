"""Download the curated book shelf from Project Gutenberg.

Resolves each book in shelf.json via the Gutendex API (https://gutendex.com),
then downloads its plain-text file to data/raw/<id>_<slug>.txt.

Idempotent: books that already exist in data/raw/ are skipped, so the script
can be re-run safely after adding books to the shelf.

Usage:
    uv run python ingestion/download.py
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

GUTENDEX_URL = "https://gutendex.com/books/"
REPO_ROOT = Path(__file__).resolve().parent.parent
SHELF_PATH = REPO_ROOT / "ingestion" / "shelf.json"
RAW_DIR = REPO_ROOT / "data" / "raw"
REQUEST_DELAY_SECONDS = 1.0  # be polite to Gutenberg's mirrors
REQUEST_TIMEOUT_SECONDS = 60


def load_shelf() -> list[dict[str, Any]]:
    with SHELF_PATH.open() as f:
        return json.load(f)["books"]


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def fetch_metadata(book_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Fetch Gutendex metadata for all books in one query (paginated)."""
    metadata: dict[int, dict[str, Any]] = {}
    url: str | None = GUTENDEX_URL
    params: dict[str, str] | None = {"ids": ",".join(str(i) for i in book_ids)}
    while url:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        page = resp.json()
        for book in page["results"]:
            metadata[book["id"]] = book
        url = page["next"]  # subsequent pages carry the ids in the URL
        params = None
    return metadata


def pick_text_url(formats: dict[str, str]) -> str | None:
    """Prefer UTF-8 plain text; fall back to any plain-text format."""
    for mime, url in formats.items():
        if mime.startswith("text/plain") and "utf-8" in mime:
            return url
    for mime, url in formats.items():
        if mime.startswith("text/plain"):
            return url
    return None


def download_book(book: dict[str, Any], text_url: str, dest: Path) -> None:
    resp = requests.get(text_url, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    resp.encoding = resp.encoding or "utf-8"
    dest.write_text(resp.text, encoding="utf-8")


def main() -> int:
    shelf = load_shelf()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Shelf: {len(shelf)} books → {RAW_DIR}")
    metadata = fetch_metadata([book["id"] for book in shelf])

    failures = 0
    for book in shelf:
        book_id, title = book["id"], book["title"]
        dest = RAW_DIR / f"{book_id}_{slugify(title)}.txt"
        if dest.exists():
            print(f"  skip  {book_id:>6}  {title} (already downloaded)")
            continue

        meta = metadata.get(book_id)
        if meta is None:
            print(f"  FAIL  {book_id:>6}  {title}: not found on Gutendex")
            failures += 1
            continue

        text_url = pick_text_url(meta["formats"])
        if text_url is None:
            print(f"  FAIL  {book_id:>6}  {title}: no plain-text format")
            failures += 1
            continue

        download_book(book, text_url, dest)
        size_kb = dest.stat().st_size // 1024
        print(f"  ok    {book_id:>6}  {title} ({size_kb} KB)")
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Done: {len(shelf) - failures}/{len(shelf)} books in {RAW_DIR}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
