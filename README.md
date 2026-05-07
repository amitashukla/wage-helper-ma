# MA Wage Theft Chatbot

A RAG-powered chatbot helping Massachusetts workers understand wage theft rights under Chapter 149 and related statutes. Uses the MA AG's enforcement data and official publications to provide cited, statute-backed answers.

---

## Monorepo Structure

```
├── frontend/        React + Vite + TypeScript (deployed to Vercel)
├── backend/         FastAPI + Python (deployed to Railway)
├── data/
│   ├── raw/         complaints.csv + enforcements.csv (gitignored)
│   ├── processed/   Normalized JSON outputs from ingestion scripts
│   ├── publications/ Downloaded AG guidance PDFs + manifest.json
│   └── statutes/    Versioned Chapter 149 JSON chunks
├── scripts/         Data ingestion, scraping, and embedding scripts
└── embeddings/      Versioned flat-file statute embeddings (.npy)
```

---

## Prerequisites

- Node.js 20+
- Python 3.11+
- Vercel CLI (`npm i -g vercel`)
- Railway CLI (`npm i -g @railway/cli`)
- Groq account with Llama 3.3 70B access

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values.

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key |
| `DATABASE_URL` | Railway Postgres connection string |
| `EMBEDDING_MODEL` | Must be `sentence-transformers/all-MiniLM-L6-v2` |
| `STATUTE_VERSION` | Date string of statute version to load, e.g. `20250101` |
| `VITE_API_URL` | (frontend only) Railway backend URL |

---

## Data Ingestion

Run scripts in this order:

```bash
# 1. Validate CSV structure
python scripts/validate_data.py

# 2. Download AG publications
python scripts/download_publications.py

# 3. Scrape and chunk Chapter 149
python scripts/scrape_statute.py

# 4. Embed statute chunks + publications
python scripts/embed_statutes.py

# 5. Ingest CSVs into Postgres
python scripts/ingest_csv.py
```

**Expected CSV columns:**

`complaints.csv`: `Received Date, Employer Name, Employer City, Employer State, Employer Zip Code, Industry, Complaint Type, ...` (one column per violation type, `Number`)

`enforcements.csv`: `Date Issued, Employer, DBA, Individual, Business City, Business State, Business ZipCode, Citation #, Violation, Violation Description, Intent, Total Assessed, Case Paid in Full, # of Employees, Industry`

---

## Run Locally

**Backend:**
```bash
cd /path/to/wage-helper-ma
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

If backend runs on a non-default port in dev, set:
```bash
VITE_DEV_API_PROXY=http://localhost:8010 npm run dev
```

---

## Deployment

**Backend (Railway):**
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set env vars: `GROQ_API_KEY`, `DATABASE_URL`, `STATUTE_VERSION`
- Use always-on plan (no cold starts)
- Health check: `GET /health`

**Frontend (Vercel):**
- Build command: `npm run build`, output dir: `dist`
- Set env var: `VITE_API_URL` to Railway backend URL (required in production)
- Auto-deploys on push to `main`

---

## Data Freshness & Re-ingestion

- **Statutes:** Re-run `scrape_statute.py` + `embed_statutes.py` when Chapter 149 is amended. Update `STATUTE_VERSION` env var. Old versioned files stay in the repo.
- **CSVs:** Re-run `validate_data.py` then `ingest_csv.py` when new AG enforcement data is available.
- **Embeddings:** If `all-MiniLM-L6-v2` is ever replaced, the entire corpus must be re-embedded. Do not swap the embedding model without re-ingesting everything.

---

## Fallback Behavior

All unhandled errors direct users to the free legal clinic:
https://www.mass.gov/info-details/free-wage-theft-legal-clinic

---

## Legal Disclaimer

This tool provides legal **information**, not legal **advice**. Always consult a qualified attorney for guidance on your specific situation.
