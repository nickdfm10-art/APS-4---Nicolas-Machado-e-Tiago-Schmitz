"""Utilitário para confirmar (commit) alterações tratando erros do banco."""
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from exceptions import ConflitoError


def confirmar(db: Session, mensagem_conflito: str) -> None:
    """Executa o commit.

    - IntegrityError (UNIQUE, FK...): desfaz a transação e devolve um conflito (409)
      com uma mensagem amigável, sem expor detalhes técnicos do banco.
    - Qualquer outra falha de persistência: desfaz a transação e propaga; o main.py
      responde 500 com mensagem genérica.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflitoError(mensagem_conflito)
    except SQLAlchemyError:
        db.rollback()
        raise
