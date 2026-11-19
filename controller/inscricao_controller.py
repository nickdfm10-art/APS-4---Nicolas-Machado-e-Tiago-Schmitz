from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_ADMIN, RESPOSTAS_AUTENTICADO
from database import get_db
from schema.erro_schema import ErroResponse
from schema.inscricao_schema import InscricaoResponse, InscritoResponse
from security.dependencies import apenas_administrador, get_usuario_atual
from service import inscricao_service

router = APIRouter(tags=["Inscrições"])


@router.post("/eventos/{evento_id}/inscricoes/{participante_id}",
             response_model=InscricaoResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_usuario_atual)],
             responses={
                 **RESPOSTAS_AUTENTICADO,
                 404: {"model": ErroResponse, "description": "Evento ou participante não encontrado."},
                 409: {"model": ErroResponse,
                       "description": "Participante já inscrito ou evento sem vagas."},
             },
             summary="Inscrever participante em um evento (autenticado)")
def inscrever(evento_id: int, participante_id: int, db: Session = Depends(get_db)):
    return inscricao_service.inscrever(db, evento_id, participante_id)


@router.get("/eventos/{evento_id}/inscricoes",
            response_model=list[InscritoResponse],
            dependencies=[Depends(apenas_administrador)],
            responses={**RESPOSTAS_ADMIN,
                       404: {"model": ErroResponse, "description": "Evento não encontrado."}},
            summary="Listar participantes inscritos em um evento (administrador)")
def listar_inscritos(evento_id: int, db: Session = Depends(get_db)):
    return inscricao_service.listar_inscritos(db, evento_id)


@router.delete("/eventos/{evento_id}/inscricoes/{participante_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(apenas_administrador)],
               responses={**RESPOSTAS_ADMIN,
                          404: {"model": ErroResponse,
                                "description": "Evento, participante ou inscrição não encontrados."}},
               summary="Cancelar inscrição (administrador)")
def cancelar_inscricao(evento_id: int, participante_id: int, db: Session = Depends(get_db)):
    inscricao_service.cancelar(db, evento_id, participante_id)
