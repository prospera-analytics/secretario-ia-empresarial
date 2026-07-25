from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.campanha_produto import CampanhaProduto
    from database.models.venda import Venda


class Campanha(Base):
    """Representa uma campanha promocional da empresa."""

    __tablename__ = "campanha"

    __table_args__ = (
        CheckConstraint(
            "data_fim >= data_inicio",
            name="ck_campanha_periodo_valido",
        ),
        CheckConstraint(
            "investimento >= 0",
            name="ck_campanha_investimento_nao_negativo",
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

    descricao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    canal: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    data_inicio: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    data_fim: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    investimento: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="planejada",
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

    campanhas_produtos: Mapped[list["CampanhaProduto"]] = relationship(
        back_populates="campanha",
        cascade="all, delete-orphan",
    )

    vendas: Mapped[list["Venda"]] = relationship(
        back_populates="campanha",
    )

    def __repr__(self) -> str:
        return (
            f"Campanha(id={self.id!r}, nome={self.nome!r}, "
            f"canal={self.canal!r}, status={self.status!r})"
        )