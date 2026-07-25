from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.compra import Compra


class Fornecedor(Base):
    """Representa um fornecedor de produtos."""

    __tablename__ = "fornecedor"

    __table_args__ = (
        CheckConstraint(
            "prazo_entrega_dias >= 0",
            name="ck_fornecedor_prazo_entrega_nao_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    cidade: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )

    prazo_entrega_dias: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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

    compras: Mapped[list["Compra"]] = relationship(
        back_populates="fornecedor",
    )

    def __repr__(self) -> str:
        return (
            f"Fornecedor(id={self.id!r}, nome={self.nome!r}, "
            f"cidade={self.cidade!r}, estado={self.estado!r}, "
            f"prazo_entrega_dias={self.prazo_entrega_dias!r})"
        )