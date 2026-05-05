"""SQLAlchemy models for the wage-helper-ma database."""

from sqlalchemy import Column, Integer, String, Date, Numeric, Text, ARRAY
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CivilEnforcement(Base):
    """Model for the civil_enforcement table — AG enforcement citation data."""

    __tablename__ = "civil_enforcement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_issued = Column(Date, nullable=True)
    employer_raw = Column(String(500), nullable=False)
    employer_normalized = Column(String(500), nullable=False, index=True)
    dba = Column(String(500), nullable=True)
    individual = Column(String(300), nullable=True)
    business_city = Column(String(200), nullable=True)
    business_state = Column(String(10), nullable=True)
    business_zipcode = Column(String(20), nullable=True)
    citation_number = Column(String(100), nullable=True)
    violation_code = Column(String(100), nullable=True)
    violation_description = Column(Text, nullable=True)
    violation_category = Column(String(200), nullable=True, index=True)
    intent = Column(String(100), nullable=True)
    total_assessed = Column(Numeric(12, 2), nullable=True)
    case_paid_in_full = Column(String(50), nullable=True)
    num_employees = Column(Integer, nullable=True)
    industry = Column(String(200), nullable=True)

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
    employer_name = Column(String(500), nullable=False)
    employer_name_normalized = Column(String(500), nullable=False, index=True)
    employer_city = Column(String(200), nullable=True)
    employer_state = Column(String(10), nullable=True)
    employer_zip = Column(String(20), nullable=True)
    industry = Column(String(200), nullable=True)
    complaint_type = Column(String(200), nullable=True)
    violation_types = Column(ARRAY(String), nullable=True)  # list of active violation flags
    number = Column(String(50), nullable=True)  # case/reference number

    def __repr__(self) -> str:
        return f"<Complaint(id={self.id}, employer={self.employer_name!r}, date={self.received_date})>"
