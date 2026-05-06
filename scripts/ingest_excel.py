"""Phase 1D — Ingest civil enforcement CSV into Postgres and processed JSON."""

import json
import re
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.db.connection import engine, SessionLocal
from backend.db.models import Base, CivilEnforcement

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "enforcements.csv"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_JSON = PROCESSED_DIR / "civil_enforcement.json"

# Abbreviation expansions for employer name normalization
ABBREVIATIONS = {
    r"\binc\b": "incorporated",
    r"\bllc\b": "limited liability company",
    r"\bcorp\b": "corporation",
    r"\bco\b": "company",
    r"\bd/b/a\b": "doing business as",
}

# Canonical violation category mapping
# Keys are lowercased substrings found in Violation Description;
# values are the canonical category.
VIOLATION_CATEGORIES = {
    "failure to pay prevailing wage": "Prevailing Wage Violation",
    "failure to pay minimum wage": "Minimum Wage Violation",
    "minimum wage": "Minimum Wage Violation",
    "failure to pay overtime": "Overtime Violation",
    "overtime": "Overtime Violation",
    "failure to furnish suitable pay slip": "Pay Stub Violation",
    "pay stub": "Pay Stub Violation",
    "pay slip": "Pay Stub Violation",
    "failure to keep true and accurate payroll records": "Record Keeping Violation",
    "payroll records": "Record Keeping Violation",
    "failure to pay wages": "Wage Payment Violation",
    "non-payment": "Wage Payment Violation",
    "failure to make timely payment": "Timely Payment Violation",
    "timely payment": "Timely Payment Violation",
    "retaliation": "Retaliation",
    "misclassification": "Misclassification",
    "child labor": "Child Labor Violation",
    "tips": "Tips Violation",
    "sunday and holiday premium pay": "Sunday/Holiday Pay Violation",
    "earned sick time": "Earned Sick Time Violation",
}


def clean_str(value) -> str | None:
    """Strip a CSV cell value; return None for empty/NaN/'nan'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return None if (not s or s.lower() == "nan") else s


def parse_date(value) -> object:
    """Parse a date value, returning None instead of NaT."""
    s = clean_str(value)
    if not s:
        return None
    try:
        result = pd.to_datetime(s, format="mixed", errors="coerce")
        return None if pd.isna(result) else result
    except Exception:
        return None


def normalize_employer_name(name: str) -> str:
    """Normalize employer name: strip, lowercase, remove punctuation, expand abbreviations."""
    if not name or pd.isna(name):
        return ""
    name = name.strip().lower()
    # Remove punctuation except alphanumeric, spaces, and slashes (for d/b/a before expansion)
    # First expand abbreviations, then strip punctuation
    for pattern, expansion in ABBREVIATIONS.items():
        name = re.sub(pattern, expansion, name)
    # Now remove remaining punctuation
    name = re.sub(r"[^\w\s]", "", name)
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def map_violation_category(description: str) -> str:
    """Map a violation description to a canonical category."""
    if not description or pd.isna(description):
        return "Other"
    desc_lower = description.strip().lower()
    for substring, category in VIOLATION_CATEGORIES.items():
        if substring in desc_lower:
            return category
    return "Other"


def parse_currency(value: str) -> float | None:
    """Parse currency string like '$12,500.00' to float."""
    if not value or pd.isna(value):
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value).strip())
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    """Parse integer string, returning None for empty/invalid."""
    if not value or pd.isna(value):
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def ingest_enforcements(path: Path = RAW_PATH) -> None:
    """Load enforcements CSV, normalize, and write to Postgres + JSON."""
    df = pd.read_csv(path, dtype=str, encoding="cp1252")
    df.columns = df.columns.str.strip()

    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db_records = []
    json_records = []
    for _, row in df.iterrows():
        employer_raw = clean_str(row.get("Employer")) or ""
        date_issued = parse_date(row.get("Date Issued"))
        violation_desc = clean_str(row.get("Violation Description"))
        total_assessed = parse_currency(row.get("Total Assessed"))
        num_employees = parse_int(row.get("# of Employees"))
        fields = {
            "date_issued": date_issued,
            "employer_raw": employer_raw,
            "employer_normalized": normalize_employer_name(employer_raw),
            "dba": clean_str(row.get("DBA")),
            "individual": clean_str(row.get("Individual")),
            "business_city": clean_str(row.get("Business City")),
            "business_state": clean_str(row.get("Business State")),
            "business_zipcode": clean_str(row.get("Business ZipCode")),
            "citation_number": clean_str(row.get("Citation #")),
            "violation_code": clean_str(row.get("Violation")),
            "violation_description": violation_desc,
            "violation_category": map_violation_category(violation_desc),
            "intent": clean_str(row.get("Intent")),
            "total_assessed": total_assessed,
            "case_paid_in_full": clean_str(row.get("Case Paid in Full")),
            "num_employees": num_employees,
            "industry": clean_str(row.get("Industry")),
        }
        db_records.append(CivilEnforcement(**fields))
        json_records.append({
            **fields,
            "date_issued": date_issued.isoformat() if date_issued else None,
            "total_assessed": float(total_assessed) if total_assessed is not None else None,
        })

    # Write to Postgres
    session: Session = SessionLocal()
    try:
        session.query(CivilEnforcement).delete()
        session.add_all(db_records)
        session.commit()
        print(f"Inserted {len(db_records):,} rows into civil_enforcement table.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    # Write processed JSON
    with open(PROCESSED_JSON, "w", encoding="utf-8") as f:
        json.dump(json_records, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(json_records):,} records to {PROCESSED_JSON}")


if __name__ == "__main__":
    ingest_enforcements()
