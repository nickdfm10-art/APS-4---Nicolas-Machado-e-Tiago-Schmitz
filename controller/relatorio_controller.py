from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_ADMIN
from database import get_db
from schema.relatorio_schema import (
    CategoriaRelatorioResponse,
    CursoRelatorioResponse,
    OcupacaoEventoResponse,
)
from security.dependencies import apenas_administrador
from service import relatorio_service

# Todos os relatórios são restritos a administradores (dependência no nível do router).
router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    dependencies=[Depends(apenas_administrador)],
    responses=RESPOSTAS_ADMIN,
)


@router.get("/eventos/ocupacao", response_model=list[OcupacaoEventoResponse],
            summary="Relatório de ocupação dos eventos (administrador)")
def relatorio_ocupacao(db: Session = Depends(get_db)):
    return relatorio_service.ocupacao_eventos(db)


@router.get("/eventos/categorias", response_model=list[CategoriaRelatorioResponse],
            summary="Relatório de eventos por categoria (administrador)")
def relatorio_categorias(db: Session = Depends(get_db)):
    return relatorio_service.eventos_por_categoria(db)


@router.get("/participantes/cursos", response_model=list[CursoRelatorioResponse],
            summary="Relatório de participação por curso (administrador)")
def relatorio_cursos(db: Session = Depends(get_db)):
    return relatorio_service.participacao_por_curso(db)
