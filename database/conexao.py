from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    """Classe base de todos os modelos SQLAlchemy."""


argumentos_conexao = {}

if DATABASE_URL.startswith("sqlite"):
    argumentos_conexao = {
        "check_same_thread": False,
    }


engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=argumentos_conexao,
)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(Engine, "connect")
    def habilitar_chaves_estrangeiras_sqlite(
        dbapi_connection,
        connection_record,
    ) -> None:
        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def obter_sessao() -> Generator[Session, None, None]:
    """Fornece uma sessão e garante seu fechamento."""

    sessao = SessionLocal()

    try:
        yield sessao
    finally:
        sessao.close()