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
