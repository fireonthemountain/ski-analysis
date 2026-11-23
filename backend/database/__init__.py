"""
Database package initialization.
"""
from .connection import Base, engine, get_db, SessionLocal
from .models import User, Video, Analysis, Progress, ValidationRun, SkillLevel, ProcessingStatus


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)


__all__ = [
    "Base",
    "engine",
    "get_db",
    "SessionLocal",
    "User",
    "Video",
    "Analysis",
    "Progress",
    "ValidationRun",
    "SkillLevel",
    "ProcessingStatus",
    "create_tables",
    "drop_tables",
]
