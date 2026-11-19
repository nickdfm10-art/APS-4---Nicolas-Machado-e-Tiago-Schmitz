from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_ADMIN
from database import get_db
from schema.erro_schema import ErroResponse
from schema.usuario_schema import UsuarioCreate, UsuarioPerfilUpdate, UsuarioResponse
from security.dependencies import apenas_administrador
from service import usuario_service

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": ErroResponse,
                              "description": "Já existe um usuário com este e-mail."}},
             summary="Cadastrar usuário (público)")
def cadastrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    # Rota pública: o perfil NÃO é informado pelo cliente; todo cadastro vira 'usuario'.
    return usuario_service.criar(db, dados)


@router.get("", response_model=list[UsuarioResponse],
            dependencies=[Depends(apenas_administrador)], responses=RESPOSTAS_ADMIN,
            summary="Listar usuários (administrador)")
def listar_usuarios(db: Session = Depends(get_db)):
    return usuario_service.listar(db)


@router.patch("/{usuario_id}/perfil", response_model=UsuarioResponse,
              dependencies=[Depends(apenas_administrador)],
              responses={**RESPOSTAS_ADMIN,
                         404: {"model": ErroResponse, "description": "Usuário não encontrado."},
                         409: {"model": ErroResponse,
                               "description": "Não é possível remover o último administrador."}},
              summary="Alterar o perfil de um usuário (administrador)")
def alterar_perfil(usuario_id: int, dados: UsuarioPerfilUpdate, db: Session = Depends(get_db)):
    return usuario_service.alterar_perfil(db, usuario_id, dados.perfil)
