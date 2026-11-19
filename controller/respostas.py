"""Respostas de erro de segurança, para documentar o Swagger de forma consistente."""
from schema.erro_schema import ErroResponse

NAO_AUTENTICADO = {
    401: {"model": ErroResponse, "description": "Token ausente, inválido ou expirado."}
}
SEM_PERMISSAO = {
    403: {"model": ErroResponse, "description": "Autenticado, mas sem permissão (exige administrador)."}
}

RESPOSTAS_AUTENTICADO = {**NAO_AUTENTICADO}
RESPOSTAS_ADMIN = {**NAO_AUTENTICADO, **SEM_PERMISSAO}
