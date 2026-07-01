"""Vector store interface and the local FAISS implementation.

`VectorStore` is the seam between agent code and storage: agents only ever
see this interface. `FaissVectorStore` backs it on the laptop; Phase 4 adds
`CosmosVectorStore` behind the same interface, so FAISS never leaks into
cloud code paths.

Embedding model constants live here because every reader and writer of the
store must agree on them: vectors from a different model (or queries missing
the BGE query prefix) would search the index with garbage geometry.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
# BGE v1.5 models are trained to see short queries with this instruction prefix.
# Passages are embedded WITHOUT it.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class SearchResult:
    record: dict[str, Any]  # the chunk record as stored (chunk_id, title, text, ...)
    score: float  # cosine similarity, higher is better


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, records: list[dict[str, Any]], vectors: np.ndarray) -> None:
        """Add records with their embedding vectors (one row per record)."""

    @abstractmethod
    def search(self, vector: np.ndarray, top_k: int = 5) -> list[SearchResult]:
        """Return the top_k most similar records to a single query vector."""


class FaissVectorStore(VectorStore):
    """Exact cosine-similarity search over normalized vectors, in memory.

    IndexFlatIP computes inner products; on unit-length vectors that equals
    cosine similarity. Exact (no approximation) is fine at our scale —
    ~7.5k vectors of dim 384.
    """

    INDEX_FILENAME = "index.faiss"
    RECORDS_FILENAME = "records.jsonl"

    def __init__(self) -> None:
        self._index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self._records: list[dict[str, Any]] = []

    def upsert(self, records: list[dict[str, Any]], vectors: np.ndarray) -> None:
        if len(records) != vectors.shape[0]:
            raise ValueError(f"{len(records)} records but {vectors.shape[0]} vectors")
        self._index.add(vectors.astype(np.float32))
        self._records.extend(records)

    def search(self, vector: np.ndarray, top_k: int = 5) -> list[SearchResult]:
        query = vector.astype(np.float32).reshape(1, EMBEDDING_DIM)
        scores, indices = self._index.search(query, top_k)
        return [
            SearchResult(record=self._records[i], score=float(s))
            for s, i in zip(scores[0], indices[0], strict=True)
            if i != -1  # FAISS pads with -1 when the index holds fewer than top_k
        ]

    def __len__(self) -> int:
        return len(self._records)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(directory / self.INDEX_FILENAME))
        with (directory / self.RECORDS_FILENAME).open("w", encoding="utf-8") as f:
            for record in self._records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, directory: Path) -> "FaissVectorStore":
        store = cls()
        store._index = faiss.read_index(str(directory / cls.INDEX_FILENAME))
        with (directory / cls.RECORDS_FILENAME).open(encoding="utf-8") as f:
            store._records = [json.loads(line) for line in f]
        if store._index.ntotal != len(store._records):
            raise ValueError(
                f"Corrupt store: {store._index.ntotal} vectors "
                f"but {len(store._records)} records"
            )
        return store
