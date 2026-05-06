"""SQLAlchemy models for the wage-helper-ma database."""

from sqlalchemy import Column, Integer, String, Date, Numeric, Text, ARRAY  # noqa: F401
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CivilEnforcement(Base):
    """Model for the civil_enforcement table — AG enforcement citation data."""

    __tablename__ = "civil_enforcement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_issued = Column(Date, nullable=True)
    employer_raw = Column(Text, nullable=False)
    employer_normalized = Column(Text, nullable=False, index=True)
    dba = Column(Text, nullable=True)
    individual = Column(Text, nullable=True)
    business_city = Column(Text, nullable=True)
    business_state = Column(Text, nullable=True)
    business_zipcode = Column(Text, nullable=True)
    citation_number = Column(Text, nullable=True)
    violation_code = Column(Text, nullable=True)
    violation_description = Column(Text, nullable=True)
    violation_category = Column(Text, nullable=True, index=True)
    intent = Column(Text, nullable=True)
    total_assessed = Column(Numeric(12, 2), nullable=True)
    case_paid_in_full = Column(Text, nullable=True)
    num_employees = Column(Integer, nullable=True)
    industry = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CivilEnforcement(id={self.id}, employer='{self.employer_normalized}', "
            f"violation='{self.violation_category}')>"
        )


# ---------------------------------------------------------------------------
# Phase 1E — Complaint model
# ---------------------------------------------------------------------------


class Complaint(Base):
    """A single wage-theft complaint filed with the MA AG's office."""

    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    received_date = Column(Date, nullable=True)
    employer_name = Column(Text, nullable=True)
    employer_name_normalized = Column(Text, nullable=True, index=True)
    employer_city = Column(Text, nullable=True)
    employer_state = Column(Text, nullable=True)
    employer_zip = Column(Text, nullable=True)
    industry = Column(Text, nullable=True)
    complaint_type = Column(Text, nullable=True)
    violation_types = Column(ARRAY(String), nullable=True)
    number = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Complaint(id={self.id}, employer={self.employer_name!r}, date={self.received_date})>"
