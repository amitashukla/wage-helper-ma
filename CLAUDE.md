# CLAUDE.md — Session Context

## Project
MA Wage Theft Chatbot. RAG pipeline over MA Chapter 149 statutes + AG enforcement data + AG publications. Helps workers understand wage theft rights. See `implementation.md` for the full plan.

## Key decisions
- Frontend: React + Vite + TypeScript → Vercel
- Backend: FastAPI + Python → Railway (always-on, no cold starts)
- DB: Railway Postgres (complaints + enforcements tables)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`, flat .npy files (versioned)
- LLM: Groq, `llama-3.3-70b-versatile`
- Fuzzy match: RapidFuzz against pre-built employer index
- Session state: client-owned, sent with every request, not persisted server-side

## Data files
- `data/raw/complaints.csv` — columns: `Received Date, Employer Name, Employer City, Employer State, Employer Zip Code, Industry, Complaint Type, [one col per violation type], Number`
- `data/raw/enforcements.csv` — columns: `Date Issued, Employer, DBA, Individual, Business City, Business State, Business ZipCode, Citation #, Violation, Violation Description, Intent, Total Assessed, Case Paid in Full, # of Employees, Industry`
- All `.xlsx` references in `implementation.md` → treat as `.csv`

## Implementation rules
- Do NOT create directories before they are needed in the plan step
- Ask for user confirmation at every [AWAIT CONFIRMATION] and between numbered stages
- Update this file with new context as implementation progresses
- Do not repeat content already in `implementation.md`, `arch_plan.md`, or `decisions.md`

## Phase status
- Phase 0 Step 0.3: in progress (README, .gitignore, .env.example, CLAUDE.md created)
