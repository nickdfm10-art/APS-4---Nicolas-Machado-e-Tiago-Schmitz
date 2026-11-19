import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from model.usuario import PerfilUsuario

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

MSG_SENHA_FRACA = (
    "A senha deve ter de 8 a 128 caracteres, com pelo menos uma letra "
    "e um número ou símbolo."
)


class UsuarioCreate(BaseModel):
    """Cadastro público de usuário.

    Não existe campo 'perfil': todo cadastro público vira perfil 'usuario'.
    extra='forbid' faz a API REJEITAR (422) quem tentar enviar 'perfil' ou qualquer
    outro campo desconhecido, em vez de ignorar silenciosamente.
    """

    nome: Nome = Field(..., examples=["Aluno Exemplo"])
    email: EmailStr = Field(..., examples=["aluno@exemplo.com"])
    senha: str = Field(..., min_length=8, max_length=128, repr=False, examples=["senha_segura"])

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return valor.lower()

    @field_validator("senha")
    @classmethod
    def validar_forca_da_senha(cls, valor: str) -> str:
        tem_letra = re.search(r"[^\W\d_]", valor) is not None
        tem_nao_letra = re.search(r"[\d_]|\W", valor) is not None
        if not (tem_letra and tem_nao_letra) or not valor.strip():
            raise ValueError(MSG_SENHA_FRACA)
        return valor


class UsuarioResponse(BaseModel):
    """Dados públicos do usuário. NÃO contém senha nem hash."""

    id: int
    nome: str
    email: EmailStr
    perfil: PerfilUsuario

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UsuarioPerfilUpdate(BaseModel):
    perfil: PerfilUsuario = Field(..., examples=["administrador"])

    model_config = ConfigDict(extra="forbid", use_enum_values=True)
