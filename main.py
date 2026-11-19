import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from controller import (
    auth_controller,
    evento_controller,
    inscricao_controller,
    participante_controller,
    relatorio_controller,
    usuario_controller,
)
from database import criar_tabelas
from exceptions import ServiceError
from security.security import validar_configuracao

logger = logging.getLogger("eventos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Falha logo na inicialização se a chave secreta JWT não estiver configurada.
    validar_configuracao()
    criar_tabelas()
    yield


app = FastAPI(
    title="API de Eventos Acadêmicos",
    description=(
        "API RESTful para gerenciar eventos, participantes e inscrições, com persistência "
        "em SQLite (SQLAlchemy), relatórios consolidados, autenticação JWT e controle de "
        "acesso por perfil (administrador / usuario).\n\n"
        "**Como testar rotas protegidas:** cadastre-se em `POST /usuarios`, faça login em "
        "`POST /auth/login`, copie o `access_token` e clique em **Authorize**."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(evento_controller.router)
app.include_router(participante_controller.router)
app.include_router(inscricao_controller.router)
app.include_router(relatorio_controller.router)


@app.exception_handler(ServiceError)
async def tratar_erro_de_negocio(request: Request, exc: ServiceError):
    """401 / 403 / 404 / 409 levantados pelos services e dependências."""
    cabecalhos = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=cabecalhos
    )


@app.exception_handler(RequestValidationError)
async def tratar_erro_de_validacao(request: Request, exc: RequestValidationError):
    """422 sem devolver o valor enviado ('input'): evita ecoar senhas na resposta."""
    erros = [
        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": erros})


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_de_banco(request: Request, exc: SQLAlchemyError):
    """Falhas de persistência: detalhe técnico só no log, mensagem genérica ao cliente."""
    logger.exception("Falha de persistência em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro ao acessar o banco de dados. Tente novamente mais tarde."},
    )


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse(url="/docs")
