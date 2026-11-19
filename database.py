"""Configuração do banco de dados (SQLite + SQLAlchemy).

Responsável por:
- configurar a conexão com o SQLite;
- criar as sessões de acesso (SessionLocal);
- disponibilizar uma sessão por requisição (get_db) e liberá-la ao final;
- criar as tabelas a partir dos models (criar_tabelas).

O arquivo do banco (eventos.db) é criado na raiz do projeto. Para usar outro
local, defina a variável de ambiente EVENTOS_DATABASE_URL
(ex.: sqlite:///C:/dados/meu_banco.db).
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv(
    "EVENTOS_DATABASE_URL", f"sqlite:///{BASE_DIR / 'eventos.db'}"
)

# check_same_thread=False: o FastAPI pode atender requisições em threads diferentes.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _ativar_chaves_estrangeiras(dbapi_connection, connection_record):
    """O SQLite ignora chaves estrangeiras por padrão; aqui elas são ativadas."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Classe base de todos os models SQLAlchemy."""


def get_db():
    """Dependência do FastAPI: abre uma sessão e garante o fechamento ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    """Cria as tabelas (se ainda não existirem) a partir dos models."""
    import model  # noqa: F401  (importa os models para registrá-los no metadata)

    Base.metadata.create_all(bind=engine)
