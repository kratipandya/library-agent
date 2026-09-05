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
- [x] Phase 2 — Agents (Semantic Kernel + OpenRouter): Content + Catalog agents,
      agents-as-tools orchestrator, FastAPI `/chat` with per-session state.
      Try it: `uv run uvicorn api.app:app --reload` → http://localhost:8000/docs
- [x] Phase 3 — Terraform (Azure infra): resource group, Cosmos DB, Function
      App (Flex Consumption), Key Vault, App Insights — six modules, all
      Terraform-first except `infra/bootstrap/`'s portal/CLI-then-imported
      resources (see `docs/DECISIONS.md` 005–012). Static Web App deferred
      to Phase 5 (regional deadlock — see 011).
- [ ] Phase 4 — Backend deployment (code onto the Function App via GitHub Actions,
      migrate FAISS → Cosmos)
- [ ] Phase 5 — Frontend (Static Web App) + observability
