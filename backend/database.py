import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required PostgreSQL environment variable is missing: {name}")
    return value


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=require_env("POSTGRES_USER"),
    password=require_env("POSTGRES_PASSWORD"),
    host=require_env("POSTGRES_HOST"),
    port=int(require_env("POSTGRES_PORT")),
    database=require_env("POSTGRES_DB"),
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()