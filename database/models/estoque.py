from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.produto import Produto


class Estoque(Base):
    """Representa o estoque atual de um produto."""

    __tablename__ = "estoque"

    __table_args__ = (
        CheckConstraint(
            "quantidade_atual >= 0",
            name="ck_estoque_quantidade_atual_nao_negativa",
        ),
        CheckConstraint(
            "estoque_minimo >= 0",
            name="ck_estoque_minimo_nao_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produto.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    quantidade_atual: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    estoque_minimo: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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

    produto: Mapped["Produto"] = relationship(
        back_populates="estoque",
    )

    def __repr__(self) -> str:
        return (
            f"Estoque(id={self.id!r}, produto_id={self.produto_id!r}, "
            f"quantidade_atual={self.quantidade_atual!r}, "
            f"estoque_minimo={self.estoque_minimo!r})"
        )