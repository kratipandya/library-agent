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

## 003 — Phase 1 complete: local RAG proof (2026-07-02)

Pipeline: Gutendex download (20 books) → boilerplate strip → chunk (7,470 chunks, max
452 tokens) → embed (bge-small-en-v1.5, 153s on laptop) → FAISS `IndexFlatIP` over
normalized vectors (exact cosine — no approximate index needed at 7.5k × 384 dims).

**`VectorStore` interface defined now, not in Phase 4.** Two methods (`upsert`, `search`);
`FaissVectorStore` is the first implementation. Defining the seam while there's only one
implementation is deliberate: when `CosmosVectorStore` arrives, agent code shouldn't change
at all — per the "FAISS never leaks into cloud code paths" rule.

**Retrieval quality, observed honestly** (5 test questions across genres):

- Specific questions retrieve the right passages: Gatsby's green-light closing paragraph
  ranked #1; Sun Tzu's spy chapter and Frankenstein's De Lacey cottage passages filled the
  whole top-3.
- A vague query ("how does the creature learn to speak?") matched Alice in Wonderland's
  school scenes instead of Frankenstein — embeddings can't guess which book you meant.
  This motivates the Phase 2 Content agent: it can rewrite queries with book context
  before searching.
- Meditations returned front-matter (editor's introduction, TOC) over the famous Book II
  passage — a known noise source. Candidate fix if it bothers us later: skip front-matter
  chunks at ingestion.

## 004 — Phase 2 complete: multi-agent backend (2026-07-19)

Five PRs (#8–#12): SK + OpenRouter plumbing, Content agent, Catalog agent, Orchestrator,
FastAPI endpoint. The CLAUDE.md architecture now runs locally end-to-end.

**Agents-as-tools over hand-rolled routing.** The Orchestrator is itself an SK
`ChatCompletionAgent` whose tools are the two specialists (`ask_content_agent`,
`ask_catalog_agent`). Chosen over an if/else intent classifier because the LLM can
decompose compound questions ("who wrote X and how does it end?" → both agents), rewrite
sub-questions to be self-contained (pronoun resolution from conversation context), and
explain its routing. Trade-off accepted: 2–4 LLM calls per user message — noticeable on
free-tier latency, fine for a portfolio demo.

**Grounding rule in both specialists: never answer from memory.** The Content agent must
cite retrieved chunks; the Catalog agent must call Open Library even for famous books.
Each agent also *refuses* the other's domain — that refusal is what makes routing
meaningful (and it's the seam App Insights will observe in Phase 5).

**Rate limits: read the server's hint.** First smoke test hit an upstream-saturated free
model; blind exponential backoff (5/10/20s) undershot the server's `retry_after_seconds: 29`.
`invoke_with_retry` now parses the hint and honors it. Model swappable via
`OPENROUTER_MODEL` env var — config, not code (paid off the same day it was written).

**Conversation state = SK threads keyed by session_id**, in process memory. Deliberately
dev-only; Phase 4 moves chat history to Cosmos DB. CORS is configured now so the Phase 5
frontend doesn't hit the classic first-request wall.

## 005 — Terraform bootstrap: region policy and first import (2026-08-12)

**Azure for Students has a subscription-level region allowlist**, discovered via
`az policy assignment list`, not documented anywhere we'd have thought to look first:
only `austriaeast`, `polandcentral`, `uaenorth`, `spaincentral`, `italynorth` accept new
resources — West Europe (our original plan) is rejected outright. Nothing wrong with the
subscription; it's a capacity-management policy Microsoft applies to student accounts.
**Austria East** is now the project's region for all real resources.

**The resource group's own region doesn't need to match.** `library-agent-rg` was created
in West Europe (portal, before the policy was found) and stayed there — a resource
group's location is deployment metadata, not a constraint on what it contains, so
recreating it would have been destructive for zero benefit. Storage account and
container are correctly in `austriaeast`.

**Portal creation of the storage account was blocked by the same policy** with a
generic UI error; `az storage account create --location austriaeast` succeeded
immediately via CLI. Documented here because it's a real deviation from the
portal-first plan (learning goal #3) — the manual-creation *intent* was honored (hand
constructed, not Terraform-first), just via CLI instead of clicking, once the portal
route dead-ended.

**First `terraform import` × 3, then `plan`/`apply` did real work — not a no-op
formality.** Resource group and container matched with zero drift. The storage account
showed one real diff: `min_tls_version` was `TLS1_0` (the CLI's default when the flag
is omitted) vs Terraform's schema default of `TLS1_2`. Made explicit in code rather than
relying on either default, then `apply`d — the storage account is measurably more secure
than how it was created, which is the honest point of bringing hand-made resources under
Terraform: it doesn't just record state, it surfaces drift worth fixing.

**`infra/bootstrap/` keeps local state on purpose.** It creates the very storage
account other modules will use as a remote backend — using that backend for itself is
circular. Applied rarely, `.tfstate` gitignored like any secret-adjacent file.
