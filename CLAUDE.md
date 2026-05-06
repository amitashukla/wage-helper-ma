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

## Infrastructure
- Railway project: `fulfilling-heart` (project ID: 5dd1665c-21f8-4777-bc20-1cda4914c6bb)
- Railway Postgres service: `Postgres-bz_L` — public URL in `.env` as `DATABASE_URL`
- Railway backend service: `backend` — env vars set; **GitHub auto-deploy link must be done manually in Railway dashboard** (CLI OAuth scope issue)
- Vercel: linked to `amitas-projects-900fa9ea/frontend`
- Backend internal DB URL (for Railway service): `postgresql://postgres:...@postgres-bzl.railway.internal:5432/railway`

## Phase status
- Phase 0: complete (Steps 0.3–0.5 done)
