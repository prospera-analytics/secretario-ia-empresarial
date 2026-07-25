from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.fornecedor import Fornecedor
    from database.models.produto import Produto


class Compra(Base):
    """Representa uma compra realizada junto a um fornecedor."""

    __tablename__ = "compra"

    __table_args__ = (
        CheckConstraint(
            "quantidade > 0",
            name="ck_compra_quantidade_positiva",
        ),
        CheckConstraint(
            "preco_unitario > 0",
            name="ck_compra_preco_unitario_positivo",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produto.id"),
        nullable=False,
        index=True,
    )

    fornecedor_id: Mapped[int] = mapped_column(
        ForeignKey("fornecedor.id"),
        nullable=False,
        index=True,
    )

    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    preco_unitario: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    data_compra: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    previsao_entrega: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendente",
        index=True,
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
        back_populates="compras",
    )

    fornecedor: Mapped["Fornecedor"] = relationship(
        back_populates="compras",
    )

    @property
    def valor_total(self) -> Decimal:
        return self.preco_unitario * self.quantidade

    def __repr__(self) -> str:
        return (
            f"Compra(id={self.id!r}, produto_id={self.produto_id!r}, "
            f"fornecedor_id={self.fornecedor_id!r}, "
            f"quantidade={self.quantidade!r}, status={self.status!r})"
        )