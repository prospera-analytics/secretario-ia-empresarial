from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.concorrente import Concorrente
    from database.models.produto import Produto


class PrecoConcorrente(Base):
    """Armazena uma oferta real encontrada em um site concorrente."""

    __tablename__ = "preco_concorrente"

    __table_args__ = (
        CheckConstraint(
            "preco > 0",
            name="ck_preco_concorrente_preco_positivo",
        ),
        CheckConstraint(
            "similaridade >= 0 AND similaridade <= 1",
            name="ck_preco_concorrente_similaridade_intervalo",
        ),
        CheckConstraint(
            (
                "tipo_correspondencia IN "
                "('exato', 'equivalente', "
                "'muito_similar', 'similar')"
            ),
            name="ck_preco_concorrente_tipo_correspondencia",
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

    concorrente_id: Mapped[int] = mapped_column(
        ForeignKey("concorrente.id"),
        nullable=False,
        index=True,
    )

    nome_produto_encontrado: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    preco: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    moeda: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="BRL",
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    similaridade: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )

    tipo_correspondencia: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    disponivel: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    coletado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    produto: Mapped["Produto"] = relationship(
        back_populates="precos_concorrentes",
    )

    concorrente: Mapped["Concorrente"] = relationship(
        back_populates="precos",
    )

    def __repr__(self) -> str:
        return (
            f"PrecoConcorrente(id={self.id!r}, "
            f"produto_id={self.produto_id!r}, "
            f"concorrente_id={self.concorrente_id!r}, "
            f"preco={self.preco!r}, "
            f"tipo_correspondencia={self.tipo_correspondencia!r})"
        )