from datetime import date, time
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# strip_whitespace + min_length=1: "   " (só espaços) é rejeitado como vazio.
TextoCurto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
TextoLongo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class CategoriaEvento(str, Enum):
    palestra = "Palestra"
    workshop = "Workshop"
    minicurso = "Minicurso"
    seminario = "Seminário"
    competicao = "Competição"


class EventoBase(BaseModel):
    titulo: TextoCurto = Field(..., examples=["Workshop de FastAPI"])
    descricao: TextoLongo = Field(..., examples=["Aprenda a criar APIs modernas com Python"])
    data: date = Field(..., examples=["2026-12-10"])
    horario: time = Field(..., examples=["14:00"])
    local: TextoCurto = Field(..., examples=["Laboratório 3"])
    capacidade: int = Field(..., gt=0, examples=[40])
    categoria: CategoriaEvento = Field(..., examples=["Workshop"])

    model_config = ConfigDict(use_enum_values=True)


class EventoCreate(EventoBase):
    """Dados para cadastrar um evento (o id é gerado pelo banco)."""


class EventoUpdate(EventoBase):
    """Dados para atualizar um evento (substituição completa, como no PUT)."""


class EventoResponse(EventoBase):
    id: int

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
