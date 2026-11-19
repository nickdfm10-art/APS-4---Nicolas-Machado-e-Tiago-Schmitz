from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_ADMIN, RESPOSTAS_AUTENTICADO
from database import get_db
from schema.erro_schema import ErroResponse
from schema.evento_schema import EventoCreate, EventoResponse, EventoUpdate
from security.dependencies import apenas_administrador, get_usuario_atual
from service import evento_service

router = APIRouter(prefix="/eventos", tags=["Eventos"])

NAO_ENCONTRADO = {404: {"model": ErroResponse, "description": "Evento não encontrado."}}


@router.post("", response_model=EventoResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(apenas_administrador)], responses=RESPOSTAS_ADMIN,
             summary="Cadastrar evento (administrador)")
def cadastrar_evento(dados: EventoCreate, db: Session = Depends(get_db)):
    return evento_service.criar(db, dados)


@router.get("", response_model=list[EventoResponse],
            dependencies=[Depends(get_usuario_atual)], responses=RESPOSTAS_AUTENTICADO,
            summary="Listar eventos (autenticado)")
def listar_eventos(db: Session = Depends(get_db)):
    return evento_service.listar(db)


@router.get("/{evento_id}", response_model=EventoResponse,
            dependencies=[Depends(get_usuario_atual)],
            responses={**RESPOSTAS_AUTENTICADO, **NAO_ENCONTRADO},
            summary="Consultar evento (autenticado)")
def consultar_evento(evento_id: int, db: Session = Depends(get_db)):
    return evento_service.obter_ou_404(db, evento_id)


@router.put("/{evento_id}", response_model=EventoResponse,
            dependencies=[Depends(apenas_administrador)],
            responses={**RESPOSTAS_ADMIN, **NAO_ENCONTRADO,
                       409: {"model": ErroResponse,
                             "description": "Capacidade menor que o número de inscritos."}},
            summary="Atualizar evento (administrador)")
def atualizar_evento(evento_id: int, dados: EventoUpdate, db: Session = Depends(get_db)):
    return evento_service.atualizar(db, evento_id, dados)


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(apenas_administrador)],
               responses={**RESPOSTAS_ADMIN, **NAO_ENCONTRADO,
                          409: {"model": ErroResponse, "description": "Evento possui inscrições."}},
               summary="Excluir evento (administrador)")
def excluir_evento(evento_id: int, db: Session = Depends(get_db)):
    evento_service.excluir(db, evento_id)
