# CLAUDE.md — Agentic Library Chatbot (Portfolio Project)

## Who I am and why this project exists

I'm Krati. This is a **learning-first portfolio project**, built for the project's sake — not production.
I work in AI adoption (strong theoretical AI/ML background, prior hands-on work on Amazon Bedrock
orchestration) and I'm deliberately building hands-on platform-engineering skills.

**Teach me as we go.** When we do something for the first time (a Terraform apply, a PR, a GitHub
Actions run), explain *what* we're doing and *why*, briefly. Prefer showing me the command and
letting me run it over doing everything silently. Small, reviewable steps.

## My six learning goals (optimize the workflow around these)

1. **Agentic AI orchestration** — multi-agent coordination with Semantic Kernel: routing, tool
   calling, agent-to-agent handoff, conversation state.
2. **Azure** — resource hierarchy, Functions, Cosmos DB, Static Web Apps, Key Vault, App Insights.
   I've done AZ-900-level study; connect new concepts to AWS equivalents when helpful.
3. **Terraform** — modules, state, plan/apply cycle, importing, destroying. I have a Terraform-on-Azure
   course in progress; reinforce it with real practice here.
4. **GitHub workflow** — I want to *practice* this, not have it done for me:
   creating branches, opening PRs, reviewing diffs, merging, resolving conflicts, reading
   failed Actions logs and fixing errors. **Always work branch → PR → merge, never commit
   directly to `main`.** Walk me through my first few PRs step by step.
5. **Frontend ↔ backend connection** — how a frontend calls the API, CORS, environment config,
   what actually happens between browser and Azure Function.
6. **End-to-end deployment** — from local code to a live URL via GitHub Actions.

## Project goal

An **online library chatbot** with a multi-agent backend:

- Ask about **any book's details** (author, publish date, editions, subjects) → live lookup via
  **Open Library API** (free, no key).
- Ask about the **content** of a curated shelf of ~15–25 **public-domain books** (Project
  Gutenberg, fetched via the **Gutendex API**) → RAG over embedded chunks.
- The scope limitation (content questions only for the shelf) is a **deliberate design decision** —
  document it in the README, don't fight it.

## Architecture

```
Browser (Static Web App, free tier)
   │  HTTPS/JSON
   ▼
Orchestrator  (Azure Function, Python, Semantic Kernel)
   │  routes intent
   ├── Catalog agent    → tools: search_catalog, get_book_details  (Open Library API)
   ├── Content agent    → tool:  search_book_content               (vector search)
   └── Recommender agent (PHASE 2 — do not build until phases 1–5 done)
   │
   ▼
Cosmos DB free tier  (vectors + chat history + metadata cache)
App Insights (traces) · Key Vault (secrets)
```

## Stack (confirmed — do not substitute without asking me)

| Piece | Choice | Notes |
|---|---|---|
| Agent framework | **Semantic Kernel, Python** | Azure-native; core learning goal |
| LLM | **OpenRouter** (OpenAI-compatible API) | Use `:free` model variants by default (e.g. DeepSeek/Llama/Qwen free tiers). I have €7.90 credit — treat it as a buffer, don't burn it on routine dev loops |
| Embeddings | **Local sentence-transformers** (`bge-small-en-v1.5`) | Ingestion is an offline job on my laptop; OpenRouter has no embedding models. Chosen over MiniLM for its 512-token limit + better retrieval quality (see DECISIONS.md 002) |
| Vector store | **FAISS locally → Cosmos DB vector search in cloud** | One `VectorStore` interface, two implementations. Never let FAISS leak into cloud code paths |
| Database | **Azure Cosmos DB free tier** (1000 RU/s, 25 GB) | Vectors, chat history, metadata cache — one service |
| Compute | **Azure Functions, consumption plan** (Python) | 1M free executions/month |
| Frontend | **Azure Static Web Apps, Free tier** | Simple React or vanilla JS chat UI; keep it small |
| Infra | **Terraform** | Remote state in an Azure Storage account (bootstrap manually, once) |
| Secrets | **Key Vault** + GitHub Actions secrets | OpenRouter key must never appear in code or tfvars committed to git |
| Observability | **Application Insights** | Log agent routing decisions and tool calls |
| CI/CD | **GitHub Actions** | Deploy on merge to `main` |

## Hard constraints (never violate)

- **€0 target.** Azure for Students subscription: $100 credit, expires 2027-07-01. Only free-tier /
  always-free SKUs: Functions consumption, Cosmos DB free tier (exactly one per subscription),
  Static Web Apps Free, App Insights within free grant. **No VMs, no App Service always-on plans,
  no Azure OpenAI, no AI Search paid tiers.** If a step would incur cost, stop and tell me first.
- **Always `terraform plan` and show me the plan before any `apply`.** Never `apply` or `destroy`
  without my explicit go-ahead.
- **Never commit secrets.** `.env` in `.gitignore` from commit #1.
- **Never commit directly to `main`.** Branch → PR → merge, every change.
- Handle OpenRouter free-tier rate limits with retry/backoff — don't silently switch to paid models.

## Build phases (strict order — everything works locally before Terraform runs)

1. **Local RAG proof** — `ingestion/` script: Gutendex download → clean → chunk
   (~400 tokens, ~15% overlap — sized to the embedding model's 512-token input limit) →
   embed locally → FAISS index. Query from a plain Python script. No agents, no Azure.
2. **Agents locally** — Semantic Kernel + OpenRouter. Content agent first, then Catalog agent,
   then Orchestrator routing. FastAPI or Functions Core Tools for a local HTTP endpoint.
3. **Terraform** — bootstrap tfstate storage (manual), then modules: resource-group, cosmos,
   function-app, key-vault, static-web-app, app-insights. Plan/apply with me watching.
4. **Deploy backend** — implement `CosmosVectorStore`, migrate the index, deploy Functions via
   GitHub Actions.
5. **Frontend + polish** — Static Web App, CORS config, App Insights traces, architecture diagram
   + honest README.
6. **(Phase 2, optional)** Recommender agent, evaluation harness.

## Repo conventions

- Suggested layout: `ingestion/`, `agents/`, `api/`, `frontend/`, `infra/` (Terraform),
  `.github/workflows/`, `docs/`.
- Conventional-ish commits (`feat:`, `fix:`, `infra:`, `docs:`); one topic per PR, small PRs.
- Python: `uv` or `pip` + `requirements.txt`, type hints, `ruff` for lint.
- Every phase ends with a short entry in `docs/DECISIONS.md` (what we chose and why) — this is
  portfolio evidence, help me keep it current.

## How to work with me

- Ask before large refactors or new dependencies.
- When an Actions run or deployment fails, help me **read the log and diagnose** before fixing —
  debugging is one of my learning goals.
- Prefer explicit, boring, well-named code over clever code.
- If something in this file conflicts with what I say in-session, my in-session instruction wins;
  offer to update this file so it stays accurate.
