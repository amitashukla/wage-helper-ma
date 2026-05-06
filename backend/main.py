"""FastAPI application entrypoint for the MA Wage Helper backend.

Loads environment variables from the project-root .env file, mounts
CORS middleware, includes API routers, and exposes a health-check endpoint.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root before anything else so DATABASE_URL etc. are
# available to any module imported below.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

# Routers — created in later phases (2A, 2B, 2C) and Phase 3 (chat)
from backend.routers import statute, violations, complaints, chat  # noqa: E402

app = FastAPI(
    title="MA Wage Helper API",
    description="RAG-powered chatbot API for MA wage theft rights.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in dev; tighten for production
# ---------------------------------------------------------------------------

_cors_origins_env = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(statute.router, prefix="/api")
app.include_router(violations.router, prefix="/api")
app.include_router(complaints.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["health"])
async def health_check() -> dict:
    """Confirm the API is running."""
    return {"status": "ok"}
