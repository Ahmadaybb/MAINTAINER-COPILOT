from __future__ import annotations

import os
from collections.abc import Generator
from functools import lru_cache

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infra.vault import get_app_secrets
from app.repositories.models import Base


def build_database_url() -> str:
    secrets = get_app_secrets()
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "maintainer_copilot")
    user = os.getenv("DB_USER", "maintainer_copilot")
    return f"postgresql+psycopg://{user}:{secrets.db_password}@{host}:{port}/{name}"


def create_db_engine(url: str | None = None) -> Engine:
    engine = create_engine(url or build_database_url(), pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _register_pgvector(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        register_vector(dbapi_connection)

    return engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_db_engine()


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
