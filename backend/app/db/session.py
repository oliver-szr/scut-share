from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, URL, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for future, explicitly authorized ORM models."""


def create_db_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _connection_record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine, "checkout")
    def restore_foreign_keys(connection, _record, _proxy) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def begin_item_write(session: Session) -> None:
    # SQLite has no row-level SELECT FOR UPDATE. Acquire its write lock before
    # reading business state; item edits and trade transitions share this lock.
    session.execute(text("BEGIN IMMEDIATE"))


def get_session(request: Request) -> Iterator[Session]:
    """One session per request; writes must be committed by the endpoint."""
    with request.app.state.session_factory() as session:
        yield session
