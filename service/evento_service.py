from sqlalchemy import func, select
from sqlalchemy.orm import Session

from exceptions import ConflitoError, NaoEncontradoError
from model import Evento, Inscricao
from schema.evento_schema import EventoCreate, EventoUpdate
from service.persistencia import confirmar

MSG_NAO_ENCONTRADO = "Evento não encontrado."
MSG_COM_INSCRICOES = (
    "Não é possível excluir o evento, pois existem participantes inscritos. "
    "Cancele as inscrições antes."
)


def obter_ou_404(db: Session, evento_id: int) -> Evento:
    evento = db.get(Evento, evento_id)
    if evento is None:
        raise NaoEncontradoError(MSG_NAO_ENCONTRADO)
    return evento


def contar_inscritos(db: Session, evento_id: int) -> int:
    total = db.scalar(
        select(func.count(Inscricao.id)).where(Inscricao.evento_id == evento_id)
    )
    return total or 0


def listar(db: Session) -> list[Evento]:
    return list(db.scalars(select(Evento).order_by(Evento.id)))


def criar(db: Session, dados: EventoCreate) -> Evento:
    evento = Evento(**dados.model_dump())
    db.add(evento)
    confirmar(db, "Não foi possível cadastrar o evento.")
    db.refresh(evento)
    return evento


def atualizar(db: Session, evento_id: int, dados: EventoUpdate) -> Evento:
    evento = obter_ou_404(db, evento_id)

    # Consistência das vagas: a nova capacidade não pode ficar abaixo dos inscritos.
    inscritos = contar_inscritos(db, evento_id)
    if dados.capacidade < inscritos:
        raise ConflitoError(
            f"A capacidade não pode ser menor que o número de inscritos ({inscritos})."
        )

    for campo, valor in dados.model_dump().items():
        setattr(evento, campo, valor)
    confirmar(db, "Não foi possível atualizar o evento.")
    db.refresh(evento)
    return evento


def excluir(db: Session, evento_id: int) -> None:
    evento = obter_ou_404(db, evento_id)

    # Regra adotada: evento com inscrições NÃO pode ser excluído (evita registros órfãos).
    if contar_inscritos(db, evento_id) > 0:
        raise ConflitoError(MSG_COM_INSCRICOES)

    db.delete(evento)
    confirmar(db, MSG_COM_INSCRICOES)
