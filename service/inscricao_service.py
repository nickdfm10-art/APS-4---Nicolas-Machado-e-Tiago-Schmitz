from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from exceptions import ConflitoError, NaoEncontradoError
from model import Inscricao
from service import evento_service, participante_service
from service.persistencia import confirmar

MSG_JA_INSCRITO = "Participante já está inscrito neste evento."
MSG_SEM_VAGAS = "Não existem vagas disponíveis para este evento."
MSG_INSCRICAO_NAO_ENCONTRADA = "Inscrição não encontrada."


def _buscar(db: Session, evento_id: int, participante_id: int) -> Inscricao | None:
    return db.scalar(
        select(Inscricao).where(
            Inscricao.evento_id == evento_id,
            Inscricao.participante_id == participante_id,
        )
    )


def inscrever(db: Session, evento_id: int, participante_id: int) -> Inscricao:
    # Verificações, na ordem pedida no enunciado:
    evento = evento_service.obter_ou_404(db, evento_id)               # 1. evento existe?
    participante_service.obter_ou_404(db, participante_id)            # 2. participante existe?
    if _buscar(db, evento_id, participante_id) is not None:           # 3. já inscrito?
        raise ConflitoError(MSG_JA_INSCRITO)
    inscritos = evento_service.contar_inscritos(db, evento_id)        # 4. ainda há vagas?
    if inscritos >= evento.capacidade:
        raise ConflitoError(MSG_SEM_VAGAS)

    inscricao = Inscricao(
        evento_id=evento_id,
        participante_id=participante_id,
        data_inscricao=date.today(),
    )
    db.add(inscricao)
    # UNIQUE(evento_id, participante_id) no banco protege contra duplicidade simultânea.
    confirmar(db, MSG_JA_INSCRITO)
    db.refresh(inscricao)
    return inscricao


def listar_inscritos(db: Session, evento_id: int) -> list[dict]:
    """Participantes inscritos em um evento, usando o relacionamento Inscricao -> Participante."""
    evento_service.obter_ou_404(db, evento_id)
    inscricoes = db.scalars(
        select(Inscricao)
        .options(joinedload(Inscricao.participante))
        .where(Inscricao.evento_id == evento_id)
        .order_by(Inscricao.id)
    ).all()
    return [
        {
            "inscricao_id": i.id,
            "data_inscricao": i.data_inscricao,
            "participante": i.participante,
        }
        for i in inscricoes
    ]


def cancelar(db: Session, evento_id: int, participante_id: int) -> None:
    evento_service.obter_ou_404(db, evento_id)
    participante_service.obter_ou_404(db, participante_id)
    inscricao = _buscar(db, evento_id, participante_id)
    if inscricao is None:
        raise NaoEncontradoError(MSG_INSCRICAO_NAO_ENCONTRADA)
    db.delete(inscricao)
    confirmar(db, "Não foi possível cancelar a inscrição.")
