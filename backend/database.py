"""
Database connection setup.

This schema uses PostgreSQL-specific features (UUID/gen_random_uuid,
partial unique indexes, window functions, generate_series) so it
requires real Postgres - SQLite will not work here.

Free option: Supabase or Neon (both have a free Postgres tier).
1. Create a project, grab the connection string.
2. Run db/schema.sql against it once (psql or the provider's SQL editor)
   to create tables and seed the 100 demo facilities + a year of data.
3. Set DATABASE_URL in a .env file next to this script, e.g.:
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Create a .env file with your Postgres "
        "connection string (see comments at top of database.py)."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
