from enum import Enum

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PerfilUsuario(str, Enum):
    administrador = "administrador"
    usuario = "usuario"


class Usuario(Base):
    """Conta de acesso à API. Só o HASH da senha é armazenado, nunca a senha."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('administrador', 'usuario')", name="ck_usuarios_perfil"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PerfilUsuario.usuario.value
    )
