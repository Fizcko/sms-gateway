"""Database engine and transaction scope."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from sms_gateway.settings import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine: Engine = create_engine(
            settings.database_url, pool_recycle=3600, pool_pre_ping=True
        )
        self._sessions = sessionmaker(self.engine, autoflush=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Commit on success, roll back on any error."""
        with self._sessions() as session, session.begin():
            yield session
