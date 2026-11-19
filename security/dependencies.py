"""Dependências do FastAPI para autenticação e autorização.

Centralizam a validação do token e a checagem de perfil, para que as rotas apenas
declarem o que exigem (Depends(...)) sem repetir lógica.
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from exceptions import AcessoNegadoError, NaoAutenticadoError
from model import PerfilUsuario, Usuario
from security.security import MSG_CREDENCIAIS, validar_token
from service import usuario_service

MSG_SEM_PERMISSAO = "Você não possui permissão para executar esta operação."

# auto_error=False: quem produz o erro 401 (com nossa mensagem) somos nós.
esquema_bearer = HTTPBearer(
    auto_error=False,
    description="Cole o token JWT obtido em POST /auth/login (apenas o token, sem a palavra Bearer).",
)


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Autenticação: exige 'Authorization: Bearer <token>' válido e devolve o usuário."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NaoAutenticadoError(MSG_CREDENCIAIS)

    usuario_id = validar_token(credenciais.credentials)
    usuario = usuario_service.obter_por_id(db, usuario_id)
    if usuario is None:  # token válido de um usuário que não existe mais
        raise NaoAutenticadoError(MSG_CREDENCIAIS)
    return usuario


def exigir_perfil(*perfis_permitidos: PerfilUsuario):
    """Autorização: cria uma dependência que só deixa passar os perfis informados (senão 403).

    O perfil considerado é o que está no BANCO, nunca algo enviado pelo cliente.
    """
    permitidos = {PerfilUsuario(p).value for p in perfis_permitidos}

    def verificador(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.perfil not in permitidos:
            raise AcessoNegadoError(MSG_SEM_PERMISSAO)
        return usuario

    return verificador


apenas_administrador = exigir_perfil(PerfilUsuario.administrador)
