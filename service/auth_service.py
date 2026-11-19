from sqlalchemy.orm import Session

from exceptions import NaoAutenticadoError
from schema.auth_schema import LoginRequest
from security.security import (
    criar_token,
    simular_verificacao_de_senha,
    verificar_senha,
)
from service import usuario_service

MSG_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."


def autenticar(db: Session, dados: LoginRequest) -> dict:
    """Valida e-mail e senha e devolve um token JWT.

    A mensagem de erro é a mesma para e-mail inexistente e senha incorreta, e o tempo
    de resposta também é equivalente (verificação simulada), para não revelar quais
    e-mails estão cadastrados.
    """
    usuario = usuario_service.obter_por_email(db, dados.email)

    if usuario is None:
        simular_verificacao_de_senha(dados.senha)
        raise NaoAutenticadoError(MSG_CREDENCIAIS_INVALIDAS)

    if not verificar_senha(dados.senha, usuario.senha_hash):
        raise NaoAutenticadoError(MSG_CREDENCIAIS_INVALIDAS)

    return {"access_token": criar_token(usuario.id), "token_type": "bearer"}
