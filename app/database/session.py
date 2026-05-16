from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# 1. Initialize the SQL Architecture Engine with Production Pool Settings
# Industrial practice: Tweak pool sizes to handle parallel Celery workers efficiently
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Keeps up to 20 permanent database connections open
    max_overflow=10,       # Allows bursting up to 30 total connections during traffic spikes
    pool_timeout=30,       # Workers wait a maximum of 30 seconds for a connection slot before failing
    pool_recycle=1800,     # Recycles idle connections every 30 minutes to prevent stale sockets
)

# 2. Bind the Session Factory Configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Contextual Dependency Provider Lifecycle Engine
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session context.
    Ensures that connections are safely returned back to the connection pool
    even if an unhandled exception occurs inside an API endpoint execution block.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # Always close the session to return it safely to the connection pool