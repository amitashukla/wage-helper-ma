"""Database connection setup using SQLAlchemy and python-dotenv."""

from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
