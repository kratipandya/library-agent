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

## 006 — First Terraform-first module: resource-group (2026-08-12)

**`infra/modules/resource-group/`** is our first reusable module (variables in →
resource → outputs), called from **`infra/main/`** — the root config every future app
resource (Cosmos, Function App, Key Vault, Static Web App, App Insights) will be added
to, one resource type per PR. Unlike `infra/bootstrap/`, this one is Terraform-first:
`library-agent-app-rg` was never clicked in the portal, only planned and applied.

**Separate resource group from bootstrap's.** `library-agent-rg` (bootstrap) now holds
only the tfstate storage account; `library-agent-app-rg` (this module) holds the actual
application resources. Split deliberately: platform/state infra and workload infra
change at different rates and have different blast radii — losing the tfstate storage
account is a very different incident than losing the Cosmos DB instance.

**`infra/main/` uses the remote backend bootstrap built**, confirmed two ways: `init`
printed no local `terraform.tfstate` (state lives in the `tfstate` container instead),
and after `apply`, `az storage blob list` showed a new `main.tfstate` blob in Azure.
Also the first time we saw Terraform's state locking in action (`Acquiring/Releasing
state lock` around the plan) — the remote backend's protection against two concurrent
applies corrupting state, unavailable with local state files.

## 007 — Cosmos DB account: two real Azure snags (2026-08-13)

`infra/modules/cosmos/` — the account only, free tier, capped at 1000 RU/s
(`capacity.total_throughput_limit`), single region. Database + containers
(vectors/chat-history/metadata-cache) follow in a separate PR. Two genuine
infrastructure problems hit on the way, neither a code bug:

**Resource providers weren't registered.** First apply failed with
`MissingSubscriptionRegistration` for `Microsoft.DocumentDB` — new/student
subscriptions only pre-register a handful of namespaces (Storage, Compute).
Registered `Microsoft.DocumentDB`, `Microsoft.Web`, `Microsoft.KeyVault`,
`Microsoft.Insights`, `Microsoft.OperationalInsights` up front (`az provider
register`) so Function App / Key Vault / App Insights won't hit this later.

**Austria East had no Cosmos DB capacity.** Second apply failed mid-creation
with `ServiceUnavailable: high demand in this region`. Worse: the failed
attempt left a broken `Failed`-state account registered on Azure (occupying
the name) even though Terraform's state never recorded it — a genuine
partial-failure gap between "Azure attempted the operation" and "Terraform
knows about it." Fixed by deleting the orphaned account directly
(`az cosmosdb delete`) and retrying in **Poland Central** instead — Cosmos
DB capacity is apparently rationed more tightly per-region than compute/
storage. `infra/main/main.tf` now has `cosmos_location` separate from
`location`: everything else stays in Austria East, Cosmos alone is in
Poland Central. Not a design preference, a capacity-availability fact.

**Lesson for future applies:** an `apply` erroring doesn't guarantee nothing
was created — check the actual resource in Azure (`az <service> show`)
before assuming a clean slate to retry from.

## 008 — Cosmos database and containers (2026-08-13)

Added to `infra/modules/cosmos/`: one SQL database (`library`, shared
throughput 400 RU/s) and three containers — `vectors`, `chat_history`,
`metadata_cache` — matching the architecture in CLAUDE.md.

**Shared database-level throughput, not per-container.** Each container
requesting its own dedicated throughput would need its own 400 RU/s
minimum — three containers would demand 1200 RU/s, past the account's
1000 RU/s cap. Database-level shared throughput lets all three containers
draw from one 400 RU/s pool instead, comfortably under the cap with room
to grow.

**Partition keys chosen to match how each container will actually be
queried:** `vectors` on `/book_id` (the Content agent's book-filtered
search), `chat_history` on `/session_id` (already how `api/app.py` keys
sessions — a straight port when Phase 4 migrates off in-memory storage),
`metadata_cache` on `/id` (a lookup cache, keyed by the item's own id).

**Vector-search indexing policy intentionally deferred** — containers exist
now, but the specifics (vector index type, embedding policy) are Phase 4's
job, decided when `CosmosVectorStore` is actually written, not guessed at
here. Applied cleanly with plan/apply cycle 4 (no incidents, unlike 007).

## 009 — Function App: Y1 blocked entirely, switched to Flex Consumption (2026-08-13)

The classic `Y1` (Dynamic Consumption) Linux plan failed identically in
**four** of our five allowed regions (`austriaeast`, `polandcentral`,
`spaincentral`, `italynorth`): `"Requested features are not supported in
region"`. Diagnosed with a direct `az rest` PUT against the ARM API for
`Microsoft.Web/serverfarms` (the CLI's own `az functionapp plan create
--sku` doesn't even accept `Y1` as a value, so that path was a dead end) —
only **UAE North** accepted the Y1+Linux combination.

UAE North then failed differently: `Current Limit (Y1 VMs): 0` — a genuine
**subscription-level compute quota of zero**, not a feature gap. Azure for
Students subscriptions default to 0 for several VM families, and this one
(`Y1 VMs`) carries extra anti-abuse restriction history (past crypto-mining
abuse), so a quota-increase request wasn't a reliable path.

**Switched to Flex Consumption (`FC1`)** — Azure's current-generation
serverless tier for Functions, a different Terraform resource entirely
(`azurerm_function_app_flex_consumption`, not `azurerm_linux_function_app`),
drawing from a separate quota pool. Applied cleanly in UAE North on the
first attempt: `python 3.12`, `maximum_instance_count = 40` (an explicit
cap on scale-out, same €0-safety philosophy as Cosmos's RU/s cap),
`instance_memory_in_mb = 2048`, deployment package stored in a dedicated
blob container (`app-package`) inside the function's own storage account.

**Every real resource in this project now spans three regions**:
`austriaeast` (resource group metadata, unaffected), `polandcentral`
(Cosmos DB), `uaenorth` (Function App). Not a design preference — each
placement is the direct result of a verified regional or quota constraint,
documented here so a future "why is this here" doesn't require
re-discovering it. Region choice per resource is decided by testing, not
assumed.

## 010 — Key Vault (2026-08-13)

`infra/modules/key-vault/` — an empty vault, no secrets in Terraform code
or state. Applied cleanly in `austriaeast` on the first try (Key Vault is
far more broadly available than the Function App consumption tiers were).

**RBAC authorization, not legacy access policies** — the modern, currently
recommended model; `rbac_authorization_enabled = true`, with a
`azurerm_role_assignment` in the root config granting the identity running
Terraform (Krati's own `az login` session, via `data
azurerm_client_config.current`) the **Key Vault Secrets Officer** role.
Access is granted by the *caller* of the module, not hardcoded inside it —
keeps the module reusable if a different principal needs access later.

**Secret values deliberately don't go through Terraform.** The OpenRouter
key will be set operationally (`az keyvault secret set`, or the portal),
not as a `.tf` resource — rotating a secret shouldn't require a `plan`/
`apply`, and a value that flows through a `.tf` file risks eventually
landing in a commit or a PR diff by accident, even gitignored. Terraform's
job here stops at "the vault exists and I can access it."

**`purge_protection_enabled = false`, paired with `purge_soft_delete_on_destroy
= true` / `recover_soft_deleted_key_vaults = true` in the root provider's
`features.key_vault` block.** A deliberate learning-project choice: Key
Vaults soft-delete by default (can't be disabled) and without purge
protection off, a `destroy` would leave a lingering soft-deleted vault
blocking the name for up to 90 days. This setup lets `terraform destroy`
fully clean up — important since practicing destroy is an explicit
CLAUDE.md goal. Would flip to `true` for anything holding real secrets.
