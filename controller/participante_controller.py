from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_ADMIN, RESPOSTAS_AUTENTICADO
from database import get_db
from schema.erro_schema import ErroResponse
from schema.participante_schema import (
    ParticipanteCreate,
    ParticipanteResponse,
    ParticipanteUpdate,
)
from security.dependencies import apenas_administrador, get_usuario_atual
from service import participante_service

router = APIRouter(prefix="/participantes", tags=["Participantes"])

NAO_ENCONTRADO = {404: {"model": ErroResponse, "description": "Participante não encontrado."}}
EMAIL_DUPLICADO = {409: {"model": ErroResponse,
                         "description": "Já existe um participante com este e-mail."}}


@router.post("", response_model=ParticipanteResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_usuario_atual)],
             responses={**RESPOSTAS_AUTENTICADO, **EMAIL_DUPLICADO},
             summary="Cadastrar participante (autenticado)")
def cadastrar_participante(dados: ParticipanteCreate, db: Session = Depends(get_db)):
    return participante_service.criar(db, dados)


@router.get("", response_model=list[ParticipanteResponse],
            dependencies=[Depends(get_usuario_atual)], responses=RESPOSTAS_AUTENTICADO,
            summary="Listar participantes (autenticado)")
def listar_participantes(db: Session = Depends(get_db)):
    return participante_service.listar(db)


@router.get("/{participante_id}", response_model=ParticipanteResponse,
            dependencies=[Depends(get_usuario_atual)],
            responses={**RESPOSTAS_AUTENTICADO, **NAO_ENCONTRADO},
            summary="Consultar participante (autenticado)")
def consultar_participante(participante_id: int, db: Session = Depends(get_db)):
    return participante_service.obter_ou_404(db, participante_id)


@router.put("/{participante_id}", response_model=ParticipanteResponse,
            dependencies=[Depends(apenas_administrador)],
            responses={**RESPOSTAS_ADMIN, **NAO_ENCONTRADO, **EMAIL_DUPLICADO},
            summary="Atualizar participante (administrador)")
def atualizar_participante(participante_id: int, dados: ParticipanteUpdate,
                           db: Session = Depends(get_db)):
    return participante_service.atualizar(db, participante_id, dados)


@router.delete("/{participante_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(apenas_administrador)],
               responses={**RESPOSTAS_ADMIN, **NAO_ENCONTRADO,
                          409: {"model": ErroResponse,
                                "description": "Participante possui inscrições."}},
               summary="Excluir participante (administrador)")
def excluir_participante(participante_id: int, db: Session = Depends(get_db)):
    participante_service.excluir(db, participante_id)
