from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Participante(Base):
    __tablename__ = "participantes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    curso: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    inscricoes: Mapped[list["Inscricao"]] = relationship(
        back_populates="participante", passive_deletes="all"
    )
