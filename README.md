# Library Agent 📚

> 🚧 **Under construction** — building in public, phase by phase.

An online library chatbot with a multi-agent backend, built as a learning-first portfolio
project: Semantic Kernel agents on Azure Functions, RAG over public-domain books, deployed
with Terraform and GitHub Actions.

## What it will do

- **Any book's details** (author, publish date, editions, subjects) → live lookup via the
  Open Library API.
- **Content questions** about a curated shelf of public-domain classics (Project Gutenberg)
  → RAG over locally-embedded chunks.

Content questions are deliberately scoped to the curated shelf — a design decision, not a
limitation to fix.

## Architecture (target)

```
Browser (Azure Static Web App)
   │  HTTPS/JSON
   ▼
Orchestrator  (Azure Function, Python, Semantic Kernel)
   ├── Catalog agent  → Open Library API
   └── Content agent  → vector search (FAISS local / Cosmos DB in cloud)
   ▼
Cosmos DB · Key Vault · App Insights
```

## Try it locally (Phase 1: semantic search over the shelf)

```bash
uv sync                                  # create venv, install pinned deps
uv run python ingestion/download.py      # fetch 20 public-domain books (Gutendex)
uv run python ingestion/clean.py         # strip Gutenberg boilerplate
uv run python ingestion/chunk.py         # ~7.5k paragraph-aware chunks, ≤460 tokens
uv run python ingestion/embed.py         # bge-small-en-v1.5 → FAISS index (~3 min)
uv run python ingestion/query.py "What does Sun Tzu say about the use of spies?"
```

Design notes and honest retrieval-quality observations live in
[docs/DECISIONS.md](docs/DECISIONS.md).

## Status

- [x] Phase 1 — Local RAG pipeline (Gutendex → chunk → embed → FAISS)
- [ ] Phase 2 — Agents (Semantic Kernel + OpenRouter)
- [ ] Phase 3 — Infrastructure (Terraform on Azure)
- [ ] Phase 4 — Backend deployment (Functions + Cosmos DB + GitHub Actions)
- [ ] Phase 5 — Frontend + observability
