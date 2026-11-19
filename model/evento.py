from datetime import date, time

from sqlalchemy import CheckConstraint, Date, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (
        CheckConstraint("capacidade > 0", name="ck_eventos_capacidade_positiva"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    horario: Mapped[time] = mapped_column(Time, nullable=False)
    local: Mapped[str] = mapped_column(String(150), nullable=False)
    capacidade: Mapped[int] = mapped_column(Integer, nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # passive_deletes="all": o SQLAlchemy não mexe nas inscrições ao excluir o evento;
    # quem protege é a FK com ON DELETE RESTRICT (e a checagem no service).
    inscricoes: Mapped[list["Inscricao"]] = relationship(
        back_populates="evento", passive_deletes="all"
    )
