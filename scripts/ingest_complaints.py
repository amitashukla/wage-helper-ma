"""Phase 1E — Ingest complaints CSV, build employer index, load into Postgres.

Usage:
    python scripts/ingest_complaints.py
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path so we can import backend modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.models import Base, Complaint  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

import os  # noqa: E402

DATABASE_URL = os.environ["DATABASE_URL"]

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "complaints.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EMPLOYER_INDEX_PATH = PROCESSED_DIR / "employer_index.json"
COMPLAINTS_JSON_PATH = PROCESSED_DIR / "complaints.json"

# Violation type columns in the CSV (boolean-ish flags)
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

# Abbreviation expansions for employer name normalization
ABBREVIATIONS = {
    r"\binc\b": "incorporated",
    r"\bllc\b": "limited liability company",
    r"\bcorp\b": "corporation",
    r"\bco\b": "company",
    r"\bltd\b": "limited",
    r"\bdba\b": "doing business as",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_employer_name(name: str) -> str:
    """Normalize an employer name for fuzzy matching.

    Steps: strip, lowercase, remove punctuation, expand abbreviations.
    """
    if not name or not isinstance(name, str):
        return ""
    n = name.strip().lower()
    # Remove punctuation (keep alphanumeric and spaces)
    n = re.sub(r"[^\w\s]", "", n)
    # Collapse multiple spaces
    n = re.sub(r"\s+", " ", n).strip()
    # Expand abbreviations
    for pattern, replacement in ABBREVIATIONS.items():
        n = re.sub(pattern, replacement, n)
    return n.strip()


def is_violation_flag_active(value) -> bool:
    """Determine if a violation column value indicates 'yes'."""
    if pd.isna(value):
        return False
    v = str(value).strip().lower()
    return v in ("yes", "y", "1", "true", "x")


def get_active_violations(row: pd.Series) -> list[str]:
    """Return list of violation type names that are flagged active for this row."""
    return [col for col in VIOLATION_COLUMNS if is_violation_flag_active(row.get(col))]


def parse_date(date_str) -> datetime | None:
    """Parse a date string from the CSV (various formats)."""
    if pd.isna(date_str) or not str(date_str).strip():
        return None
    try:
        return pd.to_datetime(str(date_str).strip(), format="mixed").to_pydatetime()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


def build_employer_index(df: pd.DataFrame) -> dict:
    """Build deduplicated employer name lookup table.

    Returns:
        {normalized_name: {"original_names": [...], "row_ids": [...]}}
    """
    index: dict[str, dict] = {}

    for idx, row in df.iterrows():
        raw_name = str(row.get("Employer Name", "")).strip()
        if not raw_name:
            continue
        norm = normalize_employer_name(raw_name)
        if not norm:
            continue

        if norm not in index:
            index[norm] = {"original_names": [], "row_ids": []}

        if raw_name not in index[norm]["original_names"]:
            index[norm]["original_names"].append(raw_name)
        index[norm]["row_ids"].append(int(idx))

    return index


def ingest_complaints(path: Path = RAW_PATH) -> None:
    """Load complaints CSV, normalize, build employer index, and store in Postgres.

    Outputs:
        - data/processed/employer_index.json
        - data/processed/complaints.json
        - Postgres table: complaints
    """
    print(f"Loading complaints from {path} ...")
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()
    print(f"  Loaded {len(df):,} rows")

    # Build employer index
    print("Building employer index ...")
    employer_index = build_employer_index(df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(EMPLOYER_INDEX_PATH, "w") as f:
        json.dump(employer_index, f, indent=2)
    print(f"  Saved employer index ({len(employer_index):,} unique normalized names) -> {EMPLOYER_INDEX_PATH}")

    # Build processed complaint records
    print("Processing complaint records ...")
    records = []
    for idx, row in df.iterrows():
        employer_raw = str(row.get("Employer Name", "")).strip()
        record = {
            "row_id": int(idx),
            "received_date": str(row.get("Received Date", "")).strip() or None,
            "employer_name": employer_raw,
            "employer_name_normalized": normalize_employer_name(employer_raw),
            "employer_city": str(row.get("Employer City", "")).strip() or None,
            "employer_state": str(row.get("Employer State", "")).strip() or None,
            "employer_zip": str(row.get("Employer Zip Code", "")).strip() or None,
            "industry": str(row.get("Industry", "")).strip() or None,
            "complaint_type": str(row.get("Complaint Type", "")).strip() or None,
            "violation_types": get_active_violations(row),
            "number": str(row.get("Number", "")).strip() or None,
        }
        records.append(record)

    # Save processed JSON
    with open(COMPLAINTS_JSON_PATH, "w") as f:
        json.dump(records, f, indent=2)
    print(f"  Saved {len(records):,} records -> {COMPLAINTS_JSON_PATH}")

    # Load into Postgres
    print("Connecting to Postgres ...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine, tables=[Complaint.__table__])
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Inserting complaint records into database ...")
    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        db_objects = []
        for rec in batch:
            obj = Complaint(
                received_date=parse_date(rec["received_date"]),
                employer_name=rec["employer_name"],
                employer_name_normalized=rec["employer_name_normalized"],
                employer_city=rec["employer_city"],
                employer_state=rec["employer_state"],
                employer_zip=rec["employer_zip"],
                industry=rec["industry"],
                complaint_type=rec["complaint_type"],
                violation_types=rec["violation_types"],
                number=rec["number"],
            )
            db_objects.append(obj)
        session.bulk_save_objects(db_objects)
        session.commit()
        print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} records)")

    session.close()
    engine.dispose()
    print("Done. Complaints ingestion complete.")


if __name__ == "__main__":
    ingest_complaints()
