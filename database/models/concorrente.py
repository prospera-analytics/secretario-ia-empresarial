from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.preco_concorrente import PrecoConcorrente


class Concorrente(Base):
    """Representa um site concorrente encontrado durante pesquisas na web."""

    __tablename__ = "concorrente"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    dominio: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    precos: Mapped[list["PrecoConcorrente"]] = relationship(
        back_populates="concorrente",
    )

    def __repr__(self) -> str:
        return (
            f"Concorrente(id={self.id!r}, nome={self.nome!r}, "
            f"dominio={self.dominio!r})"
        )