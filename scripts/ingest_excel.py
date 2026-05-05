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
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()

    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    records = []
    for _, row in df.iterrows():
        record = CivilEnforcement(
            date_issued=pd.to_datetime(
                str(row.get("Date Issued", "")).strip(), format="mixed", errors="coerce"
            ),
            employer_raw=str(row.get("Employer", "")).strip(),
            employer_normalized=normalize_employer_name(row.get("Employer", "")),
            dba=str(row.get("DBA", "")).strip() or None,
            individual=str(row.get("Individual", "")).strip() or None,
            business_city=str(row.get("Business City", "")).strip() or None,
            business_state=str(row.get("Business State", "")).strip() or None,
            business_zipcode=str(row.get("Business ZipCode", "")).strip() or None,
            citation_number=str(row.get("Citation #", "")).strip() or None,
            violation_code=str(row.get("Violation", "")).strip() or None,
            violation_description=str(row.get("Violation Description", "")).strip() or None,
            violation_category=map_violation_category(row.get("Violation Description")),
            intent=str(row.get("Intent", "")).strip() or None,
            total_assessed=parse_currency(row.get("Total Assessed")),
            case_paid_in_full=str(row.get("Case Paid in Full", "")).strip() or None,
            num_employees=parse_int(row.get("# of Employees")),
            industry=str(row.get("Industry", "")).strip() or None,
        )
        records.append(record)

    # Write to Postgres
    session: Session = SessionLocal()
    try:
        # Clear existing data and reload
        session.query(CivilEnforcement).delete()
        session.add_all(records)
        session.commit()
        print(f"Inserted {len(records):,} rows into civil_enforcement table.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    # Write processed JSON
    json_records = []
    for r in records:
        json_records.append({
            "date_issued": r.date_issued.isoformat() if r.date_issued else None,
            "employer_raw": r.employer_raw,
            "employer_normalized": r.employer_normalized,
            "dba": r.dba,
            "individual": r.individual,
            "business_city": r.business_city,
            "business_state": r.business_state,
            "business_zipcode": r.business_zipcode,
            "citation_number": r.citation_number,
            "violation_code": r.violation_code,
            "violation_description": r.violation_description,
            "violation_category": r.violation_category,
            "intent": r.intent,
            "total_assessed": r.total_assessed,
            "case_paid_in_full": r.case_paid_in_full,
            "num_employees": r.num_employees,
            "industry": r.industry,
        })

    with open(PROCESSED_JSON, "w", encoding="utf-8") as f:
        json.dump(json_records, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(json_records):,} records to {PROCESSED_JSON}")


if __name__ == "__main__":
    ingest_enforcements()
