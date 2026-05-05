# MA Wage Theft Chatbot — Architecture Decision Log

> A record of key technology and architecture choices made during planning, with brief reasoning. Intended as a reference for future contributors and for evaluating upgrades post-MVP.

---

## LLM: Llama 3.3 70B via Groq

**Chosen over:** Llama 3.1 8B (originally proposed), OpenRouter (originally proposed provider)

**Reasoning:**
- 8B models carry meaningful risk of hallucination and imprecise legal reasoning — unacceptable for a tool used by vulnerable workers making decisions about their rights
- 70B is substantially more reliable on nuanced, multi-condition legal scenarios
- Llama 3.3 70B outperforms 3.1 70B on instruction following, which matters for structured citation output
- Groq is preferred over OpenRouter because it removes a middleman, reduces latency meaningfully, and is more operationally simple
- At MVP traffic volumes, the cost difference between 8B and 70B is negligible

**Upgrade path:** Model is wrapped in `backend/services/llm.py` with a single config value — swapping models requires one line change.

**Risk to monitor:** Groq rate limits even on paid plans. Monitor usage and add queuing if needed post-MVP.

---

## Vector Search: Flat File Embeddings (no vector DB)

**Chosen over:** pgvector, Chroma, Pinecone

**Reasoning:**
- MA General Laws Chapter 149 is a bounded, static document — not a large or rapidly growing corpus
- Flat file embeddings (`.npy`) loaded into memory at startup are sufficient for this scale and faster than a round-trip to a vector DB
- Eliminates an entire infrastructure dependency for MVP
- pgvector would add operational complexity (another Railway service to manage, schema migrations) with no meaningful benefit at this scale

**Upgrade path:** If the corpus expands (e.g. AG guidance documents, case law), add pgvector to the existing Railway Postgres instance. The statute search service is designed to make this swap localized to `backend/services/statute_search.py`.

**Constraint:** Embedding model (`all-MiniLM-L6-v2`) must remain consistent between ingestion and query time. Changing it requires re-embedding the entire corpus.

---

## Search Strategy: Hybrid (Keyword Tags + Semantic Similarity)

**Chosen over:** Pure semantic search

**Reasoning:**
- Legal text contains precise terminology ("treble damages," "prevailing wage," "meal period") that semantic search can miss or conflate with related but distinct concepts
- Keyword pre-filtering on extracted tags narrows the candidate set before semantic re-ranking, improving both precision and speed
- Tags are extracted at ingestion time from a predefined list of legal terms and violation category names — low overhead, high signal

---

## Structured Data: Postgres on Railway

**Reasoning:**
- Complaints and civil enforcement data are relational and structured — a document store or key-value store would be a poor fit
- Railway makes Postgres trivial to provision alongside the backend service
- Same DB instance used for both complaints and civil enforcement data keeps infra simple

---

## Fuzzy Employer Matching: RapidFuzz against Pre-built Index

**Reasoning:**
- Workers may not know exact legal entity names of their employers ("Stop & Shop" vs. "Albertsons Companies Inc.")
- RapidFuzz provides fast, accurate fuzzy string matching with good handling of typos and common variations
- Matching runs against a pre-built normalized employer name index (not raw DB rows) to keep query-time lookups fast
- Normalization (lowercase, punctuation stripping, abbreviation expansion) applied at both index time and query time

---

## Session State: Client-Side Only

**Chosen over:** Server-side Redis, server-side in-memory storage

**Reasoning:**
- Workers using this tool may be in vulnerable situations — keeping zero server-side session data is more private and more worker-friendly
- Avoids infra dependency (no Redis instance needed for MVP)
- Railway containers can restart or redeploy; in-memory sessions would be silently lost
- Frontend holds `SessionProfile` JSON in React state and sends it with each request; server is fully stateless
- Not persisted to `localStorage` or any browser storage — state lives only for the duration of the browser session

**Trade-off:** Slightly larger request payloads; negligible at MVP scale.

---

## Prompts: Versioned Files

**Chosen over:** Hardcoded strings in application code

**Reasoning:**
- System prompt and few-shot examples are iterated on frequently, especially early in a project
- Treating them as versioned files (`backend/prompts/system.txt`, `backend/prompts/few_shot.txt`) makes changes auditable via git history and keeps them out of application logic
- Easier for non-engineers to review and edit prompt language without touching code

---

## Citation Integrity: Post-Generation Verification

**Reasoning:**
- LLMs frequently hallucinate statute section numbers or paraphrase legal text inaccurately
- For a tool with legal implications, a wrong citation is worse than no citation
- Post-generation step parses cited section numbers, looks them up in the corpus, and injects verbatim statutory text as `CitationBlock` objects
- Hallucinated citations are removed and flagged to the user

---

## Input Guardrail: Pattern Matching (No LLM Call)

**Reasoning:**
- Off-topic inputs (medical, immigration, criminal) should be rejected before any LLM call to avoid wasted tokens and user confusion
- Simple keyword/pattern matching is sufficient for MVP — no need for a classifier model
- Keeps the guardrail fast and cheap

---

## Frontend Deployment: Vercel

**Reasoning:**
- Zero-config React/Vite deployment
- Auto-deploy on push to `main` from GitHub
- No cold start concerns for static frontend

---

## Backend Deployment: Railway

**Reasoning:**
- Simple container-based Python deployment with managed Postgres
- GitHub auto-deploy integration
- **Must be on paid/always-on plan** — cold starts are unacceptable for a tool workers may rely on urgently

---

## Monorepo Structure

**Reasoning:**
- Frontend, backend, data scripts, and ingestion artifacts are tightly coupled for this project
- Single repo simplifies CI/CD, keeps data versioning alongside code, and reduces coordination overhead for a small project

---

## Statute Versioning

**Reasoning:**
- MA Legislature site is public HTML and may change layout, breaking the scraper
- Versioned statute JSON (`chapter149_v{YYYYMMDD}.json`) and versioned embeddings (`statute_embeddings_v{YYYYMMDD}.npy`) are committed to the repo
- A broken scraper does not take the system down — backend loads from last known-good version via `STATUTE_VERSION` env var
- Old versions are retained for auditability

---

## AG Workplace Rights Publications: Document Selection

**Source:** https://www.mass.gov/lists/workplace-rights-publications

**Included (24 English guidance documents across 8 categories):** MA Wage & Hour Laws Poster, Guide to Workplace Rights and Responsibilities, Anti-Retaliation Fact Sheet, Earned Sick Time Notice of Rights, Earned Sick Time eligibility and policy guides, Earned Sick Time FAQs, Child Labor Laws Poster, Guide for Working Teens, Preventing Child Labor Exploitation Fact Sheet, Notice of Rights for Domestic Workers, Workplace Rights and Protections for Domestic Workers, AG advisory on domestic violence leave, Understanding domestic violence leave, Prevailing Wage guides for workers / contractors / awarding authorities, Advisory on OSHA 10 Act, Advisory on wage and hour rights of immigrant workers, Advisory on recoupment of wage overpayments, Advisory on small necessities leave, Advisory on the Independent Contractor Law, Advisory on tips, Advisory on vacation policies, AG Advisory on labor rights in public workplaces, Information for Foreign Nationals on wage and hour compliance, U&T Visa Certification Guidance, Learn to Recognize the Signs of Labor Trafficking.

**Excluded and reasoning:**

- **Non-English versions:** Tool is English-only for MVP. Translations add corpus noise without RAG benefit since queries will be in English.
- **Labor Day Reports (2016–2025):** Broad annual enforcement summaries, not worker guidance. Large files (up to 12MB) with low signal density for per-query retrieval. Would dilute chunk quality.
- **Sample forms** (employment agreements, timesheets, work evaluations, sick time policy template, sick time verification form): Employer-facing operational templates. Contain no legal guidance text useful for answering worker questions. Would add noise to the corpus.
- **Public Bidding documents** (General Guidelines on Bid Protest Cases, FAQs): Cover the AG's internal procedures for contractor bid protests — not worker-facing rights information. No realistic worker query would retrieve these usefully.

**Upgrade path:** Non-English documents could be added post-MVP if the tool expands to support additional languages. Labor Day Reports could be mined for enforcement trend data if a separate analytics feature is added.

---

## Anonymity: Fully Anonymous

**Reasoning:**
- Target users are workers who may be in vulnerable employment situations
- No authentication, no account creation, no server-side session storage
- Lowest possible barrier to access
- A simple "I agree this is not legal advice" gate was considered and rejected in favor of a persistent UI disclaimer — requiring a click adds friction without meaningful legal benefit
