from sqlalchemy import func, select
from sqlalchemy.orm import Session

from exceptions import ConflitoError, NaoEncontradoError
from model import Inscricao, Participante
from schema.participante_schema import ParticipanteCreate, ParticipanteUpdate
from service.persistencia import confirmar

MSG_NAO_ENCONTRADO = "Participante não encontrado."
MSG_EMAIL_DUPLICADO = "Já existe um participante cadastrado com este e-mail."
MSG_COM_INSCRICOES = (
    "Não é possível excluir o participante, pois ele possui inscrições. "
    "Cancele as inscrições antes."
)


def obter_ou_404(db: Session, participante_id: int) -> Participante:
    participante = db.get(Participante, participante_id)
    if participante is None:
        raise NaoEncontradoError(MSG_NAO_ENCONTRADO)
    return participante


def _buscar_por_email(db: Session, email: str) -> Participante | None:
    return db.scalar(select(Participante).where(Participante.email == email))


def listar(db: Session) -> list[Participante]:
    return list(db.scalars(select(Participante).order_by(Participante.id)))


def criar(db: Session, dados: ParticipanteCreate) -> Participante:
    if _buscar_por_email(db, dados.email) is not None:
        raise ConflitoError(MSG_EMAIL_DUPLICADO)

    participante = Participante(**dados.model_dump())
    db.add(participante)
    # A constraint UNIQUE do banco é a garantia final (ex.: duas requisições simultâneas).
    confirmar(db, MSG_EMAIL_DUPLICADO)
    db.refresh(participante)
    return participante


def atualizar(db: Session, participante_id: int, dados: ParticipanteUpdate) -> Participante:
    participante = obter_ou_404(db, participante_id)

    outro = _buscar_por_email(db, dados.email)
    if outro is not None and outro.id != participante.id:
        raise ConflitoError(MSG_EMAIL_DUPLICADO)

    for campo, valor in dados.model_dump().items():
        setattr(participante, campo, valor)
    confirmar(db, MSG_EMAIL_DUPLICADO)
    db.refresh(participante)
    return participante


def excluir(db: Session, participante_id: int) -> None:
    participante = obter_ou_404(db, participante_id)

    total = db.scalar(
        select(func.count(Inscricao.id)).where(Inscricao.participante_id == participante_id)
    )
    # Regra adotada: participante com inscrições NÃO pode ser excluído.
    if total:
        raise ConflitoError(MSG_COM_INSCRICOES)

    db.delete(participante)
    confirmar(db, MSG_COM_INSCRICOES)
