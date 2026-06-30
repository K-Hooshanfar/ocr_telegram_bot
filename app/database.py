import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER", "ocr_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ocr_pass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ocr_db")
DB_HOST = os.getenv("DB_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DB_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
