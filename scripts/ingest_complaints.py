"""Phase 1E — Ingest complaints CSV, build employer index, load into Postgres.

Vectorized implementation: no iterrows. Uses pandas string ops + numpy for
violation flag extraction, and SQLAlchemy Core bulk insert for DB writes.

Usage:
    python scripts/ingest_complaints.py
"""

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import insert

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.connection import engine  # noqa: E402
from backend.db.models import Base, Complaint  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "complaints.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EMPLOYER_INDEX_PATH = PROCESSED_DIR / "employer_index.json"
COMPLAINTS_JSON_PATH = PROCESSED_DIR / "complaints.json"

VIOLATION_COLUMNS = [
    "Minimum Wage",
    "Tips",
    "Prevailing Wage",
    "Independent contractor misclassification",
    "Retaliation",
    "Overtime",
    "Non-payment of wages",
    "Vacation Pay",
    "Meal Period",
    "Child Labor",
    "Unpaid commissions",
    "Personnel records",
    "Other",
    "Domestic Worker Law Violation",
    "Earned Sick Leave",
    "Temp Workers' Right to Know",
    "Minor Working Too Early or Too Late",
    "Minor Working Too Many Hours",
    "Minor Working Without a Permit",
    "Minor Working in a Prohibited Occupation",
    "Minor Serving Alcohol",
    "Minor Unsupervised after 8pm",
]

_COMPLAINT_TYPE_MAP = {
    "child labor/youth employment": "Child Labor/Youth Employment",
    "child labor / youth employment": "Child Labor/Youth Employment",
    "non-payment of wage": "Non-Payment of Wage",
    "prevailing wage": "Prevailing Wage",
}

# Abbreviation pairs applied in order (order matters: longer patterns first)
_ABBREV_PAIRS = [
    (r"\bd/b/a\b", "doing business as"),
    (r"\bllc\b", "limited liability company"),
    (r"\binc\b", "incorporated"),
    (r"\bcorp\b", "corporation"),
    (r"\bltd\b", "limited"),
    (r"\bco\b", "company"),
    (r"\bdba\b", "doing business as"),
]


# ---------------------------------------------------------------------------
# Vectorized helpers
# ---------------------------------------------------------------------------


def normalize_employer_series(s: pd.Series) -> pd.Series:
    """Vectorized employer name normalization."""
    out = s.fillna("").str.strip().str.lower()
    out = out.str.replace(r"[^\w\s]", "", regex=True)
    out = out.str.replace(r"\s+", " ", regex=True).str.strip()
    for pattern, replacement in _ABBREV_PAIRS:
        out = out.str.replace(pattern, replacement, regex=True)
    return out


def normalize_str_series(s: pd.Series) -> pd.Series:
    """Strip whitespace and replace empty/'nan' with None-equivalent empty string."""
    cleaned = s.fillna("").str.strip()
    cleaned = cleaned.where(cleaned.str.lower() != "nan", "")
    return cleaned


def extract_violation_lists(df: pd.DataFrame) -> list[list[str]]:
    """Return a list of active violation column names per row, fully vectorized."""
    active_values = {"yes", "y", "1", "true", "x"}
    # Build boolean matrix: (n_rows, n_violation_cols)
    present_cols = [c for c in VIOLATION_COLUMNS if c in df.columns]
    if not present_cols:
        return [[] for _ in range(len(df))]

    bool_matrix = (
        df[present_cols]
        .fillna("")
        .apply(lambda col: col.str.strip().str.lower().isin(active_values))
        .to_numpy()
    )
    col_names = np.array(present_cols)
    return [col_names[row].tolist() for row in bool_matrix]


def build_employer_index(raw_series: pd.Series, norm_series: pd.Series) -> dict:
    """Build {normalized_name: {original_names, row_ids}} using groupby."""
    tmp = pd.DataFrame({
        "raw": raw_series.fillna("").str.strip(),
        "norm": norm_series,
        "row_id": raw_series.index,
    })
    tmp = tmp[tmp["norm"] != ""]

    index = {}
    for norm, group in tmp.groupby("norm", sort=False):
        index[norm] = {
            "original_names": group["raw"].unique().tolist(),
            "row_ids": group["row_id"].tolist(),
        }
    return index


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


def ingest_complaints(path: Path = RAW_PATH) -> None:
    print(f"Loading {path} ...")
    df = pd.read_csv(path, dtype=str, encoding="cp1252")
    df.columns = df.columns.str.strip()
    print(f"  {len(df):,} rows loaded")

    # --- Vectorized field prep ---
    print("Normalizing fields ...")
    df["emp_raw"] = normalize_str_series(df["Employer Name"])
    df["emp_norm"] = normalize_employer_series(df["Employer Name"])
    df["city"] = normalize_str_series(df.get("Employer City", pd.Series("", index=df.index)))
    df["state"] = normalize_str_series(df.get("Employer State", pd.Series("", index=df.index)))
    df["zip_"] = normalize_str_series(df.get("Employer Zip Code", pd.Series("", index=df.index)))
    df["industry_"] = normalize_str_series(df.get("Industry", pd.Series("", index=df.index)))
    df["number_"] = normalize_str_series(df.get("Number", pd.Series("", index=df.index)))

    raw_ct = normalize_str_series(df.get("Complaint Type", pd.Series("", index=df.index)))
    df["complaint_type_"] = raw_ct.str.lower().map(_COMPLAINT_TYPE_MAP).fillna(raw_ct)
    df["complaint_type_"] = df["complaint_type_"].where(
        df["complaint_type_"].notna() & (df["complaint_type_"] != ""), None
    )

    dates_parsed = pd.to_datetime(df.get("Received Date", pd.Series("", index=df.index)).str.strip(), format="mixed", errors="coerce")
    df["received_date_"] = dates_parsed

    # --- Violation lists ---
    print("Extracting violation flags ...")
    violation_lists = extract_violation_lists(df)

    # --- Employer index ---
    print("Building employer index ...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    employer_index = build_employer_index(df["Employer Name"], df["emp_norm"])
    with open(EMPLOYER_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(employer_index, f)
    print(f"  {len(employer_index):,} unique normalized employers -> {EMPLOYER_INDEX_PATH}")

    # --- Build records list (one pass, no iterrows) ---
    print("Building records ...")

    def _none(val):
        return None if (val == "" or (isinstance(val, float) and np.isnan(val))) else val

    iter_cols = ["emp_raw", "emp_norm", "city", "state", "zip_",
                 "industry_", "complaint_type_", "received_date_", "number_"]
    records = [
        {
            "received_date": None if pd.isna(row.received_date_) else row.received_date_.date(),
            "employer_name": row.emp_raw or None,
            "employer_name_normalized": row.emp_norm or None,
            "employer_city": _none(row.city),
            "employer_state": _none(row.state),
            "employer_zip": _none(row.zip_),
            "industry": _none(row.industry_),
            "complaint_type": None if pd.isna(row.complaint_type_) else row.complaint_type_,
            "violation_types": violation_lists[i],
            "number": _none(row.number_),
        }
        for i, row in enumerate(df[iter_cols].itertuples(index=False))
    ]

    # --- JSON output ---
    json_records = [
        {**r, "received_date": r["received_date"].isoformat() if r["received_date"] else None}
        for r in records
    ]
    with open(COMPLAINTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(json_records, f)
    print(f"  {len(json_records):,} records -> {COMPLAINTS_JSON_PATH}")

    # --- Postgres bulk insert via SQLAlchemy Core ---
    print("Inserting into Postgres ...")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(Complaint.__table__.delete())
        conn.execute(insert(Complaint), records)
    print(f"  Inserted {len(records):,} rows into complaints table.")
    print("Done.")


if __name__ == "__main__":
    ingest_complaints()
