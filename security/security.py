"""Funcionalidades de segurança.

- Hash e verificação de senhas: biblioteca pwdlib com Argon2 (nada é implementado
  manualmente e não se usa MD5/SHA-1).
- Tokens JWT: biblioteca PyJWT, assinatura HS256, chave secreta vinda de variável de
  ambiente (ou arquivo .env), com prazo de validade (claim "exp").

A chave secreta NUNCA fica no código-fonte. Veja o README (seção "Chave secreta").
"""
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from exceptions import NaoAutenticadoError

# Carrega o arquivo .env da raiz do projeto (se existir). Variáveis já definidas no
# ambiente do sistema têm prioridade sobre o arquivo.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ALGORITMO = "HS256"
TAMANHO_MINIMO_CHAVE = 32
EXPIRACAO_PADRAO_MINUTOS = 30
MSG_CREDENCIAIS = "Não foi possível validar as credenciais."

_hasher = PasswordHash((Argon2Hasher(),))


# ----------------------------------------------------------------- senhas
def gerar_hash_senha(senha: str) -> str:
    """Gera o hash Argon2 (com salt aleatório embutido) de uma senha."""
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha informada com o hash armazenado, usando a função da biblioteca."""
    try:
        return _hasher.verify(senha, senha_hash)
    except Exception:  # hash malformado/desconhecido: trata como senha incorreta
        return False


@lru_cache(maxsize=1)
def _hash_descartavel() -> str:
    return _hasher.hash("senha-descartavel-usada-apenas-para-equalizar-tempo")


def simular_verificacao_de_senha(senha: str) -> None:
    """Gasta o mesmo tempo de uma verificação real.

    Usada quando o e-mail não existe, para que o tempo de resposta não revele se o
    e-mail está cadastrado.
    """
    verificar_senha(senha, _hash_descartavel())


# ------------------------------------------------------------ configuração
def obter_chave_secreta() -> str:
    chave = os.getenv("JWT_SECRET_KEY", "")
    if len(chave) < TAMANHO_MINIMO_CHAVE:
        raise RuntimeError(
            "JWT_SECRET_KEY não configurada ou muito curta (mínimo de "
            f"{TAMANHO_MINIMO_CHAVE} caracteres). Gere uma chave com:\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(64))"\n'
            "e defina-a no arquivo .env (copie de .env.example) ou como variável de ambiente."
        )
    return chave


def obter_minutos_expiracao() -> int:
    bruto = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(EXPIRACAO_PADRAO_MINUTOS))
    try:
        minutos = int(bruto)
    except ValueError:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser um número inteiro.")
    if minutos <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser maior que zero.")
    return minutos


def validar_configuracao() -> None:
    """Chamada na inicialização: a API não sobe com a segurança mal configurada."""
    obter_chave_secreta()
    obter_minutos_expiracao()


# -------------------------------------------------------------------- JWT
def criar_token(usuario_id: int, expira_em: timedelta | None = None) -> str:
    """Cria um JWT assinado com: sub (id do usuário), iat (emissão) e exp (expiração).

    O perfil NÃO vai no token: ele é lido do banco a cada requisição, para que
    mudanças de permissão valham imediatamente e o cliente não possa "escolher" o perfil.
    """
    agora = datetime.now(timezone.utc)
    duracao = expira_em if expira_em is not None else timedelta(minutes=obter_minutos_expiracao())
    payload = {"sub": str(usuario_id), "iat": agora, "exp": agora + duracao}
    return jwt.encode(payload, obter_chave_secreta(), algorithm=ALGORITMO)


def validar_token(token: str) -> int:
    """Valida assinatura, algoritmo e expiração; devolve o id do usuário do token.

    Qualquer problema (token malformado, adulterado, assinado com outra chave,
    expirado, sem 'sub'/'exp') resulta em 401 com a mesma mensagem genérica.
    """
    try:
        payload = jwt.decode(
            token,
            obter_chave_secreta(),
            algorithms=[ALGORITMO],  # só HS256; rejeita "alg: none" e outros
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise NaoAutenticadoError(MSG_CREDENCIAIS)
