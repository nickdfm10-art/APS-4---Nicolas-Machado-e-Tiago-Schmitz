"""Configuração dos testes: banco SQLite temporário e chave JWT só para testes."""
import os
import tempfile
from pathlib import Path

# IMPORTANTE: definir as variáveis ANTES de importar a aplicação.
_DIR_TEMP = tempfile.mkdtemp(prefix="aps4_testes_")
ARQUIVO_BANCO = Path(_DIR_TEMP) / "teste.db"
os.environ["EVENTOS_DATABASE_URL"] = f"sqlite:///{ARQUIVO_BANCO}"
os.environ["JWT_SECRET_KEY"] = "chave-usada-somente-nos-testes-automatizados-0123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import model  # noqa: E402,F401
from database import Base, SessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from model import PerfilUsuario  # noqa: E402
from schema.usuario_schema import UsuarioCreate  # noqa: E402
from security.security import criar_token  # noqa: E402
from service import usuario_service  # noqa: E402

SENHA_TESTE = "Senha123!"


def criar_usuario_no_banco(email, perfil=PerfilUsuario.usuario, nome="Usuário Teste",
                           senha=SENHA_TESTE) -> int:
    """Cria um usuário direto pelo service (para montar cenários de permissão)."""
    db = SessionLocal()
    try:
        usuario = usuario_service.criar(
            db, UsuarioCreate(nome=nome, email=email, senha=senha), perfil=perfil
        )
        return usuario.id
    finally:
        db.close()


def cabecalho_do_usuario(usuario_id: int) -> dict:
    return {"Authorization": f"Bearer {criar_token(usuario_id)}"}


@pytest.fixture(autouse=True)
def banco_limpo():
    """Cada teste começa com as tabelas recém-criadas e vazias."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client_anonimo():
    """Cliente SEM token."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client():
    """Cliente autenticado como ADMINISTRADOR (usado pelos testes herdados da APS 3)."""
    admin_id = criar_usuario_no_banco(
        "admin@exemplo.com", PerfilUsuario.administrador, "Administrador"
    )
    with TestClient(app, headers=cabecalho_do_usuario(admin_id)) as c:
        yield c


@pytest.fixture
def client_usuario():
    """Cliente autenticado como USUÁRIO COMUM."""
    usuario_id = criar_usuario_no_banco("comum@exemplo.com", PerfilUsuario.usuario, "Usuário Comum")
    with TestClient(app, headers=cabecalho_do_usuario(usuario_id)) as c:
        yield c
