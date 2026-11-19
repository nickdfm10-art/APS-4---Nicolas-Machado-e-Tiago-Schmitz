from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Inscricao(Base):
    __tablename__ = "inscricoes"
    __table_args__ = (
        # Garante no banco que um participante não se inscreva duas vezes no mesmo evento.
        UniqueConstraint(
            "evento_id", "participante_id", name="uq_inscricao_evento_participante"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    evento_id: Mapped[int] = mapped_column(
        ForeignKey("eventos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    participante_id: Mapped[int] = mapped_column(
        ForeignKey("participantes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    data_inscricao: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )

    evento: Mapped["Evento"] = relationship(back_populates="inscricoes")
    participante: Mapped["Participante"] = relationship(back_populates="inscricoes")
