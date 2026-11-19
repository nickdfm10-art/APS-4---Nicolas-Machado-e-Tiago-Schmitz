from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=254, examples=["aluno@exemplo.com"])
    senha: str = Field(..., min_length=1, max_length=128, repr=False, examples=["senha_segura"])

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return valor.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
