from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.campanha import Campanha
    from database.models.produto import Produto


class CampanhaProduto(Base):
    """Relaciona campanhas aos produtos participantes."""

    __tablename__ = "campanha_produto"

    __table_args__ = (
        UniqueConstraint(
            "campanha_id",
            "produto_id",
            name="uq_campanha_produto",
        ),
        CheckConstraint(
            "desconto_percentual >= 0 AND desconto_percentual <= 100",
            name="ck_campanha_produto_desconto_intervalo",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    campanha_id: Mapped[int] = mapped_column(
        ForeignKey("campanha.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    desconto_percentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    campanha: Mapped["Campanha"] = relationship(
        back_populates="campanhas_produtos",
    )

    produto: Mapped["Produto"] = relationship(
        back_populates="campanhas_produtos",
    )

    def __repr__(self) -> str:
        return (
            f"CampanhaProduto(id={self.id!r}, "
            f"campanha_id={self.campanha_id!r}, "
            f"produto_id={self.produto_id!r}, "
            f"desconto_percentual={self.desconto_percentual!r})"
        )