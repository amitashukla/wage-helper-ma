"""Phase 1D — Validate civil enforcement CSV before ingestion."""

import pandas as pd
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "enforcements.csv"

REQUIRED_COLUMNS = [
    "Date Issued",
    "Employer",
    "DBA",
    "Individual",
    "Business City",
    "Business State",
    "Business ZipCode",
    "Citation #",
    "Violation",
    "Violation Description",
    "Intent",
    "Total Assessed",
    "Case Paid in Full",
    "# of Employees",
    "Industry",
]


def validate_enforcements(path: Path = RAW_PATH) -> pd.DataFrame:
    """Validate enforcements CSV structure and print summary statistics.

    Raises AssertionError with descriptive message if required columns are
    missing or renamed.
    """
    df = pd.read_csv(path, dtype=str, encoding="cp1252")

    # Strip whitespace from column names (CSV sometimes has trailing spaces)
    df.columns = df.columns.str.strip()

    # Check required columns
    actual = set(df.columns)
    expected = set(REQUIRED_COLUMNS)
    missing = expected - actual
    assert not missing, (
        f"Missing required columns in enforcements.csv: {sorted(missing)}. "
        f"Found columns: {sorted(actual)}"
    )

    # --- Summary ---
    print(f"{'='*60}")
    print("Civil Enforcement CSV Validation Summary")
    print(f"{'='*60}")
    print(f"Row count: {len(df):,}")

    # Unique violation descriptions
    violations = df["Violation Description"].str.strip().dropna().unique()
    print(f"Unique violation descriptions: {len(violations)}")

    # Date range
    dates = pd.to_datetime(df["Date Issued"].str.strip(), format="mixed", errors="coerce")
    valid_dates = dates.dropna()
    if not valid_dates.empty:
        print(f"Date range: {valid_dates.min().date()} to {valid_dates.max().date()}")
    else:
        print("Date range: no valid dates found")

    # Unique employers
    employers = df["Employer"].str.strip().dropna().unique()
    print(f"Unique employers: {len(employers)}")
    print(f"{'='*60}")

    return df


# ---------------------------------------------------------------------------
# Phase 1E — Validate complaints CSV
# ---------------------------------------------------------------------------

COMPLAINTS_RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "complaints.csv"

COMPLAINTS_REQUIRED_COLUMNS = [
    "Received Date",
    "Employer Name",
    "Employer City",
    "Employer State",
    "Employer Zip Code",
    "Industry",
    "Complaint Type",
    "Number",
]


def validate_complaints(path: Path = COMPLAINTS_RAW_PATH) -> pd.DataFrame:
    """Validate complaints CSV structure and print summary statistics.

    Raises AssertionError with descriptive message if required columns are
    missing or renamed.
    """
    df = pd.read_csv(path, dtype=str, encoding="cp1252")

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Check required columns
    actual = set(df.columns)
    expected = set(COMPLAINTS_REQUIRED_COLUMNS)
    missing = expected - actual
    assert not missing, (
        f"Missing required columns in complaints.csv: {sorted(missing)}. "
        f"Found columns: {sorted(actual)}"
    )

    # --- Summary ---
    print(f"{'='*60}")
    print("Complaints CSV Validation Summary")
    print(f"{'='*60}")
    print(f"Row count: {len(df):,}")

    # Unique complaint types
    complaint_types = df["Complaint Type"].str.strip().dropna().unique()
    print(f"Unique complaint types: {len(complaint_types)}")
    for ct in sorted(complaint_types):
        print(f"  - {ct}")

    # Unique employers
    employers = df["Employer Name"].str.strip().dropna().unique()
    print(f"Unique employers: {len(employers)}")

    # Date range
    dates = pd.to_datetime(df["Received Date"].str.strip(), format="mixed", errors="coerce")
    valid_dates = dates.dropna()
    if not valid_dates.empty:
        print(f"Date range: {valid_dates.min().date()} to {valid_dates.max().date()}")
    else:
        print("Date range: no valid dates found")

    print(f"{'='*60}")

    return df


if __name__ == "__main__":
    validate_enforcements()
    print()
    validate_complaints()
