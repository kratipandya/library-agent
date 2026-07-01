"""Strip Project Gutenberg boilerplate from downloaded books.

Every Gutenberg text wraps the actual book in a license header and footer,
delimited by "*** START/END OF THE PROJECT GUTENBERG EBOOK ... ***" markers.
This script keeps only the text between the markers, normalizes line endings,
and writes the result to data/clean/ under the same filename.

Usage:
    uv run python ingestion/clean.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
CLEAN_DIR = REPO_ROOT / "data" / "clean"

START_MARKER = re.compile(
    r"\*\*\*\s*START OF TH(?:E|IS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE
)
END_MARKER = re.compile(
    r"\*\*\*\s*END OF TH(?:E|IS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE
)


def strip_boilerplate(text: str) -> tuple[str, bool]:
    """Return the text between the Gutenberg markers.

    Falls back to the full text (flagged False) if the markers are missing
    or malformed, so a format surprise never silently drops a whole book.
    """
    start = START_MARKER.search(text)
    end = END_MARKER.search(text)
    if start is None or end is None or end.start() <= start.end():
        return text, False
    return text[start.end() : end.start()], True


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse big vertical gaps
    return text.strip()


def main() -> int:
    raw_files = sorted(RAW_DIR.glob("*.txt"))
    if not raw_files:
        print(f"No files in {RAW_DIR} — run ingestion/download.py first.")
        return 1

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    unmarked = 0
    for raw_path in raw_files:
        text = raw_path.read_text(encoding="utf-8")
        body, found_markers = strip_boilerplate(text)
        body = normalize(body)
        (CLEAN_DIR / raw_path.name).write_text(body, encoding="utf-8")

        removed_pct = 100 * (1 - len(body) / len(text))
        note = "" if found_markers else "  !! markers not found, kept full text"
        print(f"  {raw_path.name:<55} -{removed_pct:4.1f}% boilerplate{note}")
        if not found_markers:
            unmarked += 1

    print(f"Done: {len(raw_files)} books cleaned → {CLEAN_DIR}")
    if unmarked:
        print(f"Warning: {unmarked} book(s) had no Gutenberg markers — inspect them manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
