import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL is not set")
    return database_url


engine = create_engine(get_database_url(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
