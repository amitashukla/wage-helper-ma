# MA Wage Theft Chatbot — Implementation Plan

> **For Claude Code:** This plan is meant to be executed incrementally and interactively.
> Two hard stops are required before any code is written:
> 1. **Architecture & file structure confirmation** — present the proposed structure and await explicit user confirmation before proceeding.
> 2. **API keys & permissions check** — confirm all required credentials are available before writing any files.
>
> Throughout the plan, steps marked **[PARALLEL]** can be worked on simultaneously.
> Steps marked **[AWAIT CONFIRMATION]** require explicit user sign-off before proceeding.

---

## Required Credentials Checklist

Before writing any files, confirm the following are available:

- [ ] Groq API key (paid plan, Llama 3.3 70B access confirmed)
- [ ] Vercel account + CLI access (`vercel whoami`)
- [ ] Railway account + CLI access (`railway whoami`)
- [ ] GitHub repo created and accessible
- [ ] AG Excel files accessible locally:
  - `data/raw/complaints.xlsx`
  - `data/raw/civil_enforcement.xlsx`
- [ ] Expected columns confirmed in each Excel file (see Phase 1 validation step)

---

## Phase 0 — Foundation

> All subsequent phases depend on this phase. Complete fully before proceeding.

### Step 0.1 — [AWAIT CONFIRMATION] Present Architecture & File Structure

Present the following monorepo structure to the user and await explicit confirmation before creating any files:

```
ma-wage-theft-chatbot/
├── README.md
├── .env.example
├── .gitignore
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── vercel.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputBar.tsx
│   │   │   ├── Disclaimer.tsx
│   │   │   └── CitationBlock.tsx
│   │   ├── hooks/
│   │   │   └── useSession.ts
│   │   └── types/
│   │       └── index.ts
├── backend/
│   ├── requirements.txt
│   ├── railway.json
│   ├── main.py                  # FastAPI entrypoint
│   ├── prompts/
│   │   ├── system.txt           # Versioned system prompt
│   │   └── few_shot.txt         # Versioned few-shot examples
│   ├── routers/
│   │   ├── chat.py
│   │   ├── statute.py
│   │   ├── violations.py
│   │   └── complaints.py
│   ├── services/
│   │   ├── rag.py               # RAG orchestration
│   │   ├── statute_search.py    # Component 1
│   │   ├── violation_mapper.py  # Component 2
│   │   ├── complaint_lookup.py  # Component 3
│   │   ├── citation_verifier.py # Post-generation citation check
│   │   ├── input_guard.py       # Off-topic input filter
│   │   └── llm.py               # Groq client wrapper
│   ├── db/
│   │   ├── connection.py
│   │   └── models.py
│   └── session/
│       └── schema.py            # Session profile data model
├── data/
│   ├── raw/                     # Excel files (gitignored if sensitive)
│   │   ├── complaints.xlsx
│   │   └── civil_enforcement.xlsx
│   ├── processed/
│   │   ├── complaints.json
│   │   └── civil_enforcement.json
│   └── statutes/
│       └── chapter149_v{YYYYMMDD}.json   # Versioned statute chunks
├── scripts/
│   ├── scrape_statute.py
│   ├── ingest_excel.py
│   ├── embed_statutes.py
│   └── validate_data.py
└── embeddings/
    └── statute_embeddings_v{YYYYMMDD}.npy  # Versioned flat-file embeddings
```

**[AWAIT CONFIRMATION]** — Do not proceed until the user explicitly approves this structure or requests changes.

---

### Step 0.2 — [AWAIT CONFIRMATION] Confirm API Keys & Permissions

Run through the credentials checklist above. Confirm each item is available. Do not proceed until all items are checked.

---

### Step 0.3 — Initialize README & Repository

**Definition of done:** `README.md` exists with all sections below, repo is initialized, `.gitignore` and `.env.example` are committed.

Create `README.md` with the following sections:
- Project overview and purpose
- Monorepo structure overview
- Prerequisites (Node, Python version, accounts needed)
- Environment variables (mirroring `.env.example`)
- How to run ingestion scripts
- How to run backend locally
- How to run frontend locally
- Deployment (Vercel + Railway)
- Data freshness & re-ingestion notes
- Legal disclaimer note

Create `.env.example`:
```
GROQ_API_KEY=
DATABASE_URL=
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
STATUTE_VERSION=          # e.g. 20250101
```

Create `.gitignore` — exclude `data/raw/`, `.env`, `__pycache__`, `node_modules`, `.vercel`.

**README update:** Add setup instructions for the repo scaffold.

---

### Step 0.4 — Initialize Monorepo Scaffold

- Initialize frontend: `npm create vite@latest frontend -- --template react-ts`
- Initialize backend: create `backend/requirements.txt` with initial dependencies:
  - `fastapi`, `uvicorn`, `psycopg2-binary`, `sqlalchemy`, `rapidfuzz`, `sentence-transformers`, `numpy`, `pandas`, `openpyxl`, `httpx`, `playwright`, `python-dotenv`, `slowapi`
- Create `railway.json` for backend deployment config
- Create `vercel.json` for frontend deployment config
- Commit scaffold to GitHub

---

### Step 0.5 — Provision Infrastructure

- Create Railway project, provision Postgres instance
- Note Railway connection string → add to `.env`
- Connect Railway project to GitHub repo (auto-deploy on push to `main`)
- Connect Vercel project to GitHub repo (auto-deploy frontend on push to `main`)

---

## Phase 1 — Data Ingestion

> Steps 1A, 1B, and 1C are fully **[PARALLEL]** — assign or execute simultaneously.
> All three must complete before Phase 2 begins.

---

### Step 1A — [PARALLEL] Download MA AG Workplace Rights Publications

**Definition of done:** All 24 English guidance PDFs downloaded to `data/publications/`, filenames normalized, manifest file written. No sample forms, no Labor Day reports, no non-English documents.

Write `scripts/download_publications.py`:
- Download each PDF from the URLs below using `httpx` with a polite delay between requests (1–2 seconds)
- Save to `data/publications/{slug}.pdf` where slug is derived from the document title (lowercase, hyphens)
- Write a manifest file `data/publications/manifest.json` listing: `{slug, title, category, url, downloaded_at, file_size_kb}`
- Fail loudly if any download returns non-200 or file size is suspiciously small (< 10KB)

**Documents to download (24 total):**

*Wage & Hour (2):*
- Massachusetts Wage & Hour Laws Poster — `https://www.mass.gov/doc/massachusetts-wage-hour-laws-poster-english/download`
- Guide to Workplace Rights and Responsibilities — `https://www.mass.gov/doc/guide-to-workplace-rights-and-responsibilities-0/download`

*Anti-Retaliation (1):*
- Anti-Retaliation Fact Sheet — `https://www.mass.gov/doc/anti-retaliation-fact-sheet/download`

*Earned Sick Time (4):*
- Earned Sick Time Notice of Employee Rights — `https://www.mass.gov/doc/earned-sick-time-notice-of-employee-rights-english/download`
- Does your employer's earned sick time policy follow state law? — `https://www.mass.gov/doc/does-your-employers-earned-sick-time-policy-follow-state-law/download`
- Do you qualify for earned sick time? — `https://www.mass.gov/doc/do-you-qualify-for-earned-sick-time/download`
- Earned Sick Time FAQs — `https://www.mass.gov/doc/earned-sick-time-faqs/download`

*Child Labor (3):*
- Child Labor Laws Poster — `https://www.mass.gov/doc/child-labor-laws-poster/download`
- Guide for Working Teens — `https://www.mass.gov/doc/guide-for-working-teens/download`
- Preventing Child Labor Exploitation Fact Sheet — `https://www.mass.gov/doc/preventing-child-labor-exploitation-fact-sheet/download`

*Domestic Workers (2):*
- Notice of Rights for Domestic Workers — `https://www.mass.gov/doc/notice-of-rights-for-domestic-workers/download`
- Workplace Rights and Protections for Domestic Workers — `https://www.mass.gov/doc/workplace-rights-and-protections-for-domestic-workers/download`

*Domestic Violence Leave (2):*
- AG advisory on domestic violence leave — `https://www.mass.gov/doc/attorney-generals-advisory-on-domestic-violence-leave/download`
- Understanding domestic violence leave — `https://www.mass.gov/doc/understanding-domestic-violence-leave/download`

*Prevailing Wage (3):*
- MA Prevailing Wage Laws: Guide for Awarding Authorities — `https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-awarding-authorities/download`
- MA Prevailing Wage Laws: Guide for Public Construction Contractors — `https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-public-construction-contractors/download`
- MA Prevailing Wage Laws: Guide for Workers — `https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-workers/download`

*Advisories (10):*
- Advisory on the OSHA 10 Act — `https://www.mass.gov/doc/advisory-on-the-osha-10-act/download`
- Advisory on wage and hour rights of immigrant workers — `https://www.mass.gov/doc/advisory-on-the-wage-and-hour-rights-of-immigrant-workers/download`
- Advisory on recoupment of inadvertent wage overpayments — `https://www.mass.gov/doc/attorney-generals-advisory-on-recoupment-of-inadvertent-wage-overpayments/download`
- Advisory on small necessities leave — `https://www.mass.gov/doc/attorney-generals-advisory-on-small-necessities-leave/download`
- Advisory on the Independent Contractor Law — `https://www.mass.gov/doc/attorney-generals-advisory-on-the-independent-contractor-law/download`
- Advisory on tips — `https://www.mass.gov/doc/attorney-generals-advisory-on-tips/download`
- Advisory on vacation policies — `https://www.mass.gov/doc/attorney-generals-advisory-on-vacation-policies/download`
- AG Advisory: Affirming Labor Rights in Public Workplaces — `https://www.mass.gov/doc/attorney-general-advisory-affirming-labor-rights-and-obligations-in-public-workplaces-0/download`
- Information for Foreign Nationals on Wage and Hour Law Compliance — `https://www.mass.gov/doc/information-for-foreign-nationals-on-compliance-with-wage-and-hour-laws-in-massachusetts/download`
- U&T Visa Certification Guidance — `https://www.mass.gov/doc/ut-visa-certification-guidance/download`

*Labor Trafficking (1):*
- Learn to Recognize the Signs of Labor Trafficking — `https://www.mass.gov/doc/learn-to-recognize-the-signs-of-labor-trafficking/download`

**Excluded (document rationale in architecture-decisions.md):**
- All non-English versions
- Labor Day Reports (broad annual reports, not worker guidance)
- Sample forms: employment agreements, timesheets, work evaluations, sick time policy template, sick time verification form (employer-facing templates, not legal guidance)
- Public Bidding documents (AG bid protest procedures, not worker-facing)

**Versioning note:** Downloaded PDFs are committed to the repo under `data/publications/`. The manifest records download date. Re-run this script periodically to catch updated documents — compare file sizes against manifest to detect changes.

**README update:** Document the publications download step, the manifest format, and how to re-run when documents are updated.

---

### Step 1B — [PARALLEL] Publications PDF Extraction & Chunking

**Definition of done:** All 24 publications extracted to text, chunked, tagged, and appended to the statute corpus for embedding. Each chunk carries its source document slug and category.

Extend `scripts/embed_statutes.py` (or create a separate `scripts/embed_publications.py`) to:
- Extract text from each PDF using `pdfplumber` (add to `requirements.txt`)
- Chunk by section/paragraph boundaries with 50-token overlap, same strategy as statute chunking
- Tag each chunk with: document category (e.g. "earned_sick_time", "prevailing_wage"), document slug, and matched legal keyword tags
- Append to the same embeddings flat file so statute search covers both statute text and AG publications in one pass
- Store chunk metadata: `{source: "publication", slug, category, chunk_index, text, tags}`

**Note:** PDF extraction quality varies. Flag any document where extracted text is suspiciously short (possible scanned image PDF) and log a warning — these may need manual review.

---

### Step 1C — [PARALLEL] Statute Scraper & Chunking

**Definition of done:** `data/statutes/chapter149_v{YYYYMMDD}.json` exists with well-formed chunks, each containing section number, title, full text, and keyword tags. Embeddings saved to `embeddings/statute_embeddings_v{YYYYMMDD}.npy`.

#### 1A.1 — Scrape MA Legislature Chapter 149

Write `scripts/scrape_statute.py` using Playwright (handles JS rendering):
- Target: `https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXXI/Chapter149`
- Extract each section: section number, section title, full statutory text
- Output: `data/statutes/chapter149_v{YYYYMMDD}.json`

**Fragility note:** The MA Legislature site is public HTML and may change layout. The scraper should fail loudly with a clear error message if expected selectors are missing. The versioned JSON file is the source of truth — a broken scraper does not take the system down.

**Versioning:** Filename includes scrape date. Old versions are retained in the repo. A `STATUTE_VERSION` env var controls which version the backend loads at startup.

#### 1A.2 — Chunk & Tag Statute Text

Each section becomes one or more chunks. Chunking strategy:
- Split on section boundaries first
- If a section exceeds 512 tokens, split further on paragraph boundaries with 50-token overlap
- Each chunk carries: `section_id`, `section_title`, `chunk_index`, `text`, `tags`

Keyword tagging at ingestion time:
- Extract tags from a predefined list of legal terms: violation category names (see Phase 1B), section numbers, and key statutory terms (e.g. "treble damages," "meal period," "prevailing wage," "minimum wage," "overtime," "retaliation")
- Store as an array of matched tags per chunk
- Tags are used for keyword pre-filtering at query time (see Phase 2A)

#### 1A.3 — Embed Statute Chunks

Write `scripts/embed_statutes.py`:
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (fixed — must remain consistent between ingestion and query time; changing it requires re-embedding the entire corpus)
- Embed all chunks
- Save embeddings as `embeddings/statute_embeddings_v{YYYYMMDD}.npy` (versioned, committed to repo)
- Save chunk metadata (section_id, text, tags) alongside embeddings for lookup

**README update:** Document the embedding model and the re-ingestion workflow.

---

### Step 1D — [PARALLEL] Civil Enforcement Excel Ingestion

**Definition of done:** Civil enforcement records loaded into Postgres with normalized violation categories. Validation script passes.

#### 1B.1 — Validate Excel Structure

Write `scripts/validate_data.py` with a validation function for `civil_enforcement.xlsx`:
- Assert required columns exist, including `Violation description`
- Fail loudly with a descriptive error if columns are missing or renamed
- Print a summary: row count, unique violation descriptions, date range

#### 1B.2 — Normalize & Load

Write `scripts/ingest_excel.py` with a function for civil enforcement data:
- Normalize employer names: lowercase, strip punctuation, expand abbreviations (`inc` → `incorporated`, `llc` → `limited liability company`, etc.)
- Map `Violation description` values to canonical violation categories (the ~50 AG-defined categories)
- Load into Postgres table `civil_enforcement`
- Output processed JSON to `data/processed/civil_enforcement.json`

**README update:** Document expected Excel column names.

---

### Step 1E — [PARALLEL] Complaints Excel Ingestion & Employer Index

**Definition of done:** Complaint records loaded into Postgres. Normalized employer name lookup table built and stored. Validation script passes.

#### 1C.1 — Validate Excel Structure

Add a validation function to `scripts/validate_data.py` for `complaints.xlsx`:
- Assert required columns exist, including `Complaint Type` and employer name column
- Fail loudly with descriptive error if columns missing
- Print summary: row count, unique complaint types, employer count

#### 1C.2 — Normalize & Load

Add a function to `scripts/ingest_excel.py` for complaints:
- Normalize employer names using the same normalization logic as 1B.2
- Build a deduplicated employer name lookup table: `{normalized_name: [original_names, row_ids]}`
- Store lookup table as `data/processed/employer_index.json` (used by fuzzy matcher at query time)
- Load complaint records into Postgres table `complaints`
- Map `Complaint Type` to canonical complaint categories
- Output processed JSON to `data/processed/complaints.json`

**Fuzzy matching note:** RapidFuzz will run against the normalized employer name lookup table (not raw DB rows) at query time. Pre-building this index keeps query-time matching fast.

---

## Phase 2 — Backend Components

> Steps 2A, 2B, and 2C are fully **[PARALLEL]** once Phase 1 is complete.
> Each is independently testable via its own REST endpoint.
> All three must pass their definitions of done before Phase 3 begins.

---

### Step 2A — [PARALLEL] Statute Citation Search Endpoint

**Definition of done:** `GET /api/statute/search?q=...` returns a ranked list of statute chunks with section numbers, text excerpts, keyword tags, and similarity scores for 5 predefined test queries. Returns empty list (not error) when no confident results found.

Write `backend/services/statute_search.py`:
- Load statute chunks and embeddings from versioned flat files at startup (controlled by `STATUTE_VERSION` env var)
- At query time:
  1. **Keyword pre-filter:** match query against chunk tags to narrow candidate set
  2. **Semantic re-rank:** embed query using same `all-MiniLM-L6-v2` model, compute cosine similarity against candidate embeddings
  3. **Threshold:** return only chunks with cosine similarity ≥ 0.70
  4. **Fallback:** if no chunks meet threshold, return empty list — caller handles fallback logic
- Return: ranked list of `{section_id, section_title, text, tags, score}`

Wire up `backend/routers/statute.py` → `GET /api/statute/search`.

**Test queries (use these to verify done):**
1. "My employer didn't pay me for overtime"
2. "I never get a pay stub"
3. "My boss pays me less than minimum wage"
4. "I was fired for complaining about my pay"
5. "I work through my lunch break but don't get paid for it"

---

### Step 2B — [PARALLEL] Violation Category Mapper Endpoint

**Definition of done:** `POST /api/violations/map` accepts a free-text user complaint and returns the top 3 closest AG violation categories with confidence scores. Returns a fallback category of `"unknown"` with score 0 if no match found.

Write `backend/services/violation_mapper.py`:
- At startup, embed all ~50 AG violation category names and complaint types using `all-MiniLM-L6-v2`
- At query time, embed user complaint text and compute cosine similarity against category embeddings
- Return top 3 matches with scores
- Threshold: if top match score < 0.65, return `"unknown"` with score 0

Wire up `backend/routers/violations.py` → `POST /api/violations/map`.

---

### Step 2C — [PARALLEL] Employer Complaint Lookup Endpoint

**Definition of done:** `GET /api/complaints/lookup?employer=...` returns all matching complaint records for fuzzy-matched employer names, with match score and matched name shown. Returns empty list (not error) for no matches.

Write `backend/services/complaint_lookup.py`:
- Load `employer_index.json` at startup
- At query time:
  1. Normalize input employer name (same normalization as ingestion)
  2. Run RapidFuzz `process.extract` against normalized employer index, threshold score ≥ 80
  3. Retrieve matching complaint records from Postgres for all matched employer IDs
- Return: `{matched_employer, match_score, complaints: [{date, complaint_type, outcome}]}`
- Fallback: empty list if no matches above threshold

Wire up `backend/routers/complaints.py` → `GET /api/complaints/lookup`.

---

## Phase 3 — Chat Orchestration

> Depends on all of Phase 2. Begin only when 2A, 2B, and 2C are complete.

**Definition of done:** `POST /api/chat` accepts a user message and session state, returns a structured response with answer text, verified citations, violation category, employer matches, and a confidence flag. Falls back gracefully at each failure mode.

---

### Step 3.1 — Session Profile Schema

Write `backend/session/schema.py` defining the session profile as a Pydantic model:

```python
class SessionProfile(BaseModel):
    employer: Optional[str]
    employer_matches: List[str]
    complaint_types: List[str]
    employment_type: Optional[str]      # "hourly" | "salary" | "tipped"
    hours_per_week: Optional[float]
    violation_categories: List[str]
    conversation_history: List[dict]    # last 8 turns: [{role, content}]
    confidence_flag: Optional[str]      # "high" | "low" | "fallback"
```

Session state is owned entirely by the client (no server-side storage). The frontend sends the full `SessionProfile` JSON with each request and stores the updated profile returned in the response. Session state is held in React state in the frontend — it is not persisted to `localStorage` or any browser storage. It lives only for the duration of the browser session.

---

### Step 3.2 — Input Guardrail

Write `backend/services/input_guard.py`:
- Lightweight keyword/pattern check before any LLM call
- Reject clearly off-topic inputs (medical, immigration, criminal law, etc.) with a canned redirect: "This tool is specific to Massachusetts wage theft. For other legal questions, please visit [mass.gov legal aid resources]."
- Off-topic check should be fast — no LLM call, pattern matching only
- Return: `{is_valid: bool, redirect_message: Optional[str]}`

---

### Step 3.3 — Prompts as Versioned Files

Create `backend/prompts/system.txt`:
- Role: You are a legal information assistant helping Massachusetts workers understand wage theft.
- Scope: You only answer questions about MA wage law (Chapter 149 and related statutes).
- Tone: Plain language, accessible, non-judgmental.
- Constraints: Never provide legal advice. Always cite specific statute sections. Always recommend consulting a lawyer for definitive guidance. If uncertain, say so clearly.
- Fallback instruction: If you cannot find relevant statute text or are not confident in your answer, direct the user to seek free legal help at https://www.mass.gov/info-details/free-wage-theft-legal-clinic
- Disclaimer: Do not include any disclaimer text in your responses — the UI handles this.

Create `backend/prompts/few_shot.txt`:
- 3–5 example (user query → ideal structured response) pairs covering: unpaid overtime, missing pay stub, minimum wage violation, retaliation, meal break violation.

---

### Step 3.4 — LLM Client Wrapper

Write `backend/services/llm.py`:
- Groq client wrapper using `httpx`
- Model: `llama-3.3-70b-versatile`
- Constructs prompt from: system prompt + few-shot examples + session profile summary + retrieved statute chunks + conversation history (last 8 turns) + current user message
- Returns raw LLM response text
- On Groq API error: raise a typed `LLMUnavailableError` (handled by RAG orchestrator)

---

### Step 3.5 — Citation Verifier

Write `backend/services/citation_verifier.py`:
- After LLM generates a response, parse out any statute section references (e.g. "Section 148", "§ 148")
- For each cited section, look up the verbatim text in the loaded statute chunks
- If section exists: inject a `CitationBlock` into the response containing the verbatim statute text and section number
- If section does not exist in corpus: remove the hallucinated citation from the response and add a note: "Note: this section could not be verified — please confirm with a legal professional."
- Return: `{response_text, citation_blocks: [{section_id, section_title, verbatim_text}], hallucinated_citations_removed: bool}`

---

### Step 3.6 — RAG Orchestrator

Write `backend/services/rag.py` — this is the core pipeline:

```
Input: user_message, session_profile

1. Input guard check
   → If off-topic: return redirect message, skip all below

2. [PARALLEL] Run simultaneously:
   a. Statute citation search (2A) on user_message
   b. Violation category mapping (2B) on user_message
   c. Employer complaint lookup (2C) if session_profile.employer is set

3. Evaluate retrieval results:
   → If statute search returns no results above threshold AND violation mapper returns "unknown":
      set confidence_flag = "fallback"
      return legal clinic URL: https://www.mass.gov/info-details/free-wage-theft-legal-clinic
   → If statute search returns results but violation mapper is "unknown":
      set confidence_flag = "low"
   → Otherwise:
      set confidence_flag = "high"

4. If not fallback:
   a. Assemble context: statute chunks + violation categories + employer complaints + session profile summary
   b. Call LLM (llm.py)
   c. If LLMUnavailableError: return legal clinic URL fallback
   d. Run citation verifier on LLM response
   e. Update session profile: employer, complaint_types, violation_categories, conversation_history

5. Return structured response:
   {
     answer: str,
     citation_blocks: [...],
     violation_categories: [...],
     employer_matches: [...],
     confidence_flag: "high" | "low" | "fallback",
     session_profile: updated SessionProfile
   }
```

Wire up `backend/routers/chat.py` → `POST /api/chat`.

---

### Step 3.7 — Rate Limiting

Add `slowapi` rate limiting to `POST /api/chat`:
- 20 requests per minute per IP (adjust based on observed usage)
- Return HTTP 429 with message: "Too many requests. Please wait a moment before continuing."

---

## Phase 4 — React Frontend

> Can begin in parallel with Phase 3 once Phase 0 is complete, using mocked API responses.
> Full integration requires Phase 3 to be complete.

**Definition of done:** Chat UI renders correctly, sends messages to `/api/chat`, displays responses with citation blocks, shows disclaimer, links to legal clinic, preserves session state in React state for the duration of the browser session.

---

### Step 4.1 — Session Hook

Write `frontend/src/hooks/useSession.ts`:
- Manages `SessionProfile` state in React (`useState`)
- Exposes: `sessionProfile`, `updateSessionProfile(newProfile)`
- No persistence — state is lost on page refresh (intentional: privacy-first, fully anonymous)

---

### Step 4.2 — Types

Write `frontend/src/types/index.ts`:
- `SessionProfile` matching backend schema
- `ChatMessage`: `{role: "user" | "assistant", content: string, citationBlocks?: CitationBlock[], confidenceFlag?: string}`
- `CitationBlock`: `{section_id, section_title, verbatim_text}`
- `ChatResponse`: matching backend response shape

---

### Step 4.3 — Components

Create files incrementally as listed. Full component responsibility reference is in `TARGET_ARCHITECTURE.md`.

**`components/layout/ChatWindow.tsx`**
- Outer container for the chat interface
- Renders the message list, mapping over `ChatMessage[]`
- Manages scroll-to-bottom on new message
- Renders `TypingIndicator` when awaiting a response
- Renders `SessionPill` below the header when session tags exist

**`components/layout/Sidebar.tsx`**
- Right-hand panel, always visible alongside the message list
- Renders `SuggestedNextSteps` when next steps are available
- Renders a static "Free legal help" section with a link to the legal clinic URL
- Renders empty/placeholder state before first response

**`components/chat/MessageBubble.tsx`**
- Shell component only: renders avatar, bubble wrapper, and routes to either a plain user text bubble or `BotMessage`
- Does not contain any bot response logic itself

**`components/chat/BotMessage.tsx`**
- Composes the full bot response in order: `VerdictBanner` → prose text → `ViolationCategoryBadge[]` → `PriorComplaintsCallout` → `CitationBlock`
- Each sub-component is conditionally rendered based on response data

**`components/chat/TypingIndicator.tsx`**
- Three-dot animated loading indicator
- Rendered by `ChatWindow` while `isLoading` is true

**`components/chat/VerdictBanner.tsx`**
- Renders the verdict bar at the top of each bot response
- Three visual variants based on `confidence_flag`: green ("This looks like a violation") / muted ("We found limited matches") / fallback (direct legal clinic link)

**`components/chat/ViolationCategoryBadge.tsx`**
- Single teal pill rendering one violation category name
- Rendered as a list inside `BotMessage` when `violation_categories` is non-empty

**`components/chat/PriorComplaintsCallout.tsx`**
- Amber callout box showing prior AG complaint count and summary for a matched employer
- Conditionally rendered only when `employer_matches` is non-empty

**`components/chat/CitationBlock.tsx`**
- Collapsible citation component: collapsed by default, expands on "See relevant statute text" toggle
- Renders `section_id`, `section_title`, and `verbatim_text` as separate elements
- Labeled "From MA General Laws Chapter 149"

**`components/input/InputBar.tsx`**
- Textarea + send button
- Disabled while `isLoading` is true
- On submit: calls `POST /api/chat` with message + current session profile, updates session profile from response
- Renders static disclaimer text and legal clinic link below the input row — not a separate component

**`components/input/InputHints.tsx`**
- Renders rotating starter prompt chips above the textarea
- Hidden after the user sends their first message

**`components/session/SessionPill.tsx`**
- Renders the "What I know" tag strip
- Maps over `session_summary[]` strings as individual tags
- Hidden until at least one tag exists in session state

**`components/sidebar/SuggestedNextSteps.tsx`**
- Maps over `suggested_next_steps[]` strings returned by the backend
- Each renders as a button that calls `sendMessage` with that question as the user's next input
- Renders empty state ("Ask me anything about your situation") before first response

---

### Step 4.4 — App Assembly

Wire together in `App.tsx`:
- `useSession` hook at top level
- `ChatWindow` + `InputBar` + `Disclaimer` layout
- Configure API base URL from environment variable (`VITE_API_URL`)

**README update:** Document frontend environment variables and local dev setup.

---

## Phase 5 — Integration, Hardening & Deployment

> All prior phases must be complete. No parallelization — work through sequentially.

---

### Step 5.1 — End-to-End Integration Testing

Run the following test scenarios manually and verify correct behavior:

| Scenario | Expected behavior |
|---|---|
| "My employer hasn't paid me overtime" | Statute citations returned, overtime violation category matched |
| "I work at McDonald's and never get pay stubs" | Employer match attempted, pay record violation category matched |
| "My boss fired me for complaining about pay" | Retaliation statute section cited |
| Clearly off-topic input ("I need immigration help") | Input guard redirect, no LLM call |
| Gibberish / low-confidence input | Fallback to legal clinic URL |
| Groq API unavailable (simulate with bad key) | Fallback to legal clinic URL, no 500 error |
| 21st request within 1 minute from same IP | HTTP 429 returned |

---

### Step 5.2 — Deployment

**Backend (Railway):**
- Confirm `railway.json` start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set environment variables in Railway dashboard: `GROQ_API_KEY`, `DATABASE_URL`, `STATUTE_VERSION`
- Confirm always-on (not hobby tier — cold starts are unacceptable for this use case)
- Verify health check endpoint: `GET /health` returns 200

**Frontend (Vercel):**
- Set `VITE_API_URL` to Railway backend URL
- Confirm build command: `npm run build`, output dir: `dist`
- Verify CORS headers on backend allow Vercel domain

---

### Step 5.3 — Final README Update

Ensure README covers:
- All environment variables (frontend and backend)
- How to re-run ingestion scripts when Excel files are updated
- How to re-scrape and re-embed statutes (and how to update `STATUTE_VERSION`)
- Deployment checklist (Railway always-on, Vercel env vars)
- Known limitations and fallback behavior
- Link to legal clinic: https://www.mass.gov/info-details/free-wage-theft-legal-clinic

---

## Fallback Behavior Summary

| Failure mode | Behavior |
|---|---|
| Off-topic input | Input guard redirect message, no LLM call |
| No statute chunks above similarity threshold (< 0.70) AND violation mapper unknown | Return legal clinic URL directly |
| Statute chunks found but violation mapper unknown | Return answer with `confidence_flag = "low"`, soft warning in UI |
| Hallucinated statute citation | Remove citation, add verification note in response |
| Groq API unavailable | Return legal clinic URL directly |
| No employer match found | Continue without employer context, no error |
| Rate limit exceeded | HTTP 429, prompt user to wait |
| **Final fallback (any unhandled error)** | Direct user to https://www.mass.gov/info-details/free-wage-theft-legal-clinic |

---

## Data Freshness Notes

- **Statute:** Re-run `scripts/scrape_statute.py` and `scripts/embed_statutes.py` when Chapter 149 is amended. Update `STATUTE_VERSION` env var. Old versions remain in repo.
- **Excel files:** Re-run `scripts/ingest_excel.py` when new AG data is available. Validate first with `scripts/validate_data.py`.
- **Embeddings:** If `all-MiniLM-L6-v2` is ever swapped for a different model, the entire corpus must be re-embedded. Do not change the embedding model without re-ingesting everything.
