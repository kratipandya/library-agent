# Decision Log

Short entries, newest last. What we chose, what we rejected, and why — portfolio evidence
of deliberate engineering decisions.

## 001 — Project setup (2026-07-01)

**Stack** is fixed in [CLAUDE.md](../CLAUDE.md): Semantic Kernel (Python) agents, OpenRouter
free-tier LLMs, local sentence-transformers embeddings, FAISS → Cosmos DB vector store behind
one interface, Azure Functions consumption + Static Web Apps free tier, Terraform, GitHub
Actions. Driving constraints: €0 budget and six explicit learning goals.

Setup decisions made today:

- **uv over pip + venv** — one tool for venv, dependencies, and lockfile (`uv.lock` gives
  reproducible installs); faster; good current-practice signal for a portfolio.
- **Public repo from day one** — the commit/PR history is itself portfolio evidence; also
  enables free branch protection on `main` (PRs mandatory, no direct pushes, admins included).
- **No Homebrew (for now)** — admin password unavailable; installed `gh` as a standalone
  binary in `~/.local/bin` instead. Terraform and Azure CLI can be installed the same way in
  Phase 3, so nothing blocks on this.
- **Python 3.12** (pinned in `.python-version`) — matches local pyenv and is GA-supported on
  Azure Functions.
- **Ruff** for linting/import-sorting with rules E, W, F, I, UP, B at line length 100.

## 002 — Embedding model and chunk size (2026-07-02)

**Chose `bge-small-en-v1.5` with ~400-token chunks and ~60-token (~15%) overlap**, replacing
CLAUDE.md's original "500–800 tokens" guess.

Why: embedding models silently truncate input past their limit — MiniLM at 256 tokens,
bge-small at 512. A 700-token chunk embedded by MiniLM would index only its first third;
the rest becomes unsearchable with no error anywhere. Sizing chunks *to the model*
(400 + 60 overlap = 460 worst case, under 512) removes that failure mode entirely.
bge-small-en-v1.5 also outscores MiniLM on retrieval benchmarks (MTEB) at a similar size.

Token counts come from the model's own tokenizer (not word-count approximations), so the
"fits in the model" guarantee is exact. Chunking is paragraph-aware — split on blank lines,
pack paragraphs up to the limit, sentence-split only over-long paragraphs — because
paragraph boundaries are where prose naturally changes topic.
