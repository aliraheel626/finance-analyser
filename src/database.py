"""Database configuration and session management."""

from sqlmodel import Session, SQLModel, create_engine

from src.config import settings

# Create engine with SQLite
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Initialize database tables."""
    # Import models to register them with SQLModel
    from src.models import Transaction  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)
