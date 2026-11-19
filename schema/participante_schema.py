from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Curso = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ParticipanteBase(BaseModel):
    nome: Nome = Field(..., examples=["Maria Souza"])
    email: EmailStr = Field(..., examples=["maria@email.com"])
    curso: Curso = Field(..., examples=["Engenharia de Software"])

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        # E-mails são guardados em minúsculas para a unicidade não depender de maiúsculas.
        return valor.lower()

    @field_validator("curso")
    @classmethod
    def normalizar_curso(cls, valor: str) -> str:
        # Remove espaços duplicados ("Engenharia  de   Software" -> "Engenharia de Software").
        return " ".join(valor.split())


class ParticipanteCreate(ParticipanteBase):
    """Dados para cadastrar um participante."""


class ParticipanteUpdate(ParticipanteBase):
    """Dados para atualizar um participante (substituição completa)."""


class ParticipanteResponse(ParticipanteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
