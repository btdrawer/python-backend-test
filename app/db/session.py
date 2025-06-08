from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

from app.core.config import settings

Base = declarative_base()

def get_engine():
    return create_engine(str(settings.DATABASE_URL))

def get_session_local():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

# Dependency
def get_db() -> Generator:
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
