from pydantic import BaseModel


class ErroResponse(BaseModel):
    """Formato padrão das respostas de erro (usado na documentação do Swagger)."""

    detail: str
