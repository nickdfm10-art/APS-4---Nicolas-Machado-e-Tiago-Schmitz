from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controller.respostas import RESPOSTAS_AUTENTICADO
from database import get_db
from model import Usuario
from schema.auth_schema import LoginRequest, TokenResponse
from schema.erro_schema import ErroResponse
from schema.usuario_schema import UsuarioResponse
from security.dependencies import get_usuario_atual
from service import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse,
             responses={401: {"model": ErroResponse, "description": "E-mail ou senha inválidos."}},
             summary="Autenticar e obter o token JWT (público)")
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.autenticar(db, dados)


@router.get("/me", response_model=UsuarioResponse, responses=RESPOSTAS_AUTENTICADO,
            summary="Dados do usuário autenticado")
def meus_dados(usuario: Usuario = Depends(get_usuario_atual)):
    # O usuário vem do TOKEN validado; o cliente não informa nenhum id.
    return usuario
