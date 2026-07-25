from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.conexao import Base

if TYPE_CHECKING:
    from database.models.campanha_produto import CampanhaProduto
    from database.models.compra import Compra
    from database.models.estoque import Estoque
    from database.models.preco_concorrente import PrecoConcorrente
    from database.models.venda import Venda


class Produto(Base):
    """Representa um smartphone comercializado pela empresa."""

    __tablename__ = "produto"

    __table_args__ = (
        CheckConstraint(
            "armazenamento_gb > 0",
            name="ck_produto_armazenamento_positivo",
        ),
        CheckConstraint(
            "preco_venda > 0",
            name="ck_produto_preco_venda_positivo",
        ),
    )

    # Chave primária da tabela
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Smartphone",
    )

    marca: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    armazenamento_gb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    descricao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    preco_venda: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
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

    estoque: Mapped["Estoque | None"] = relationship(
        back_populates="produto",
        uselist=False,
        cascade="all, delete-orphan",
    )

    compras: Mapped[list["Compra"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
    )

    vendas: Mapped[list["Venda"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
    )

    precos_concorrentes: Mapped[list["PrecoConcorrente"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
    )

    campanhas_produtos: Mapped[list["CampanhaProduto"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Produto(id={self.id!r}, "
            f"nome={self.nome!r}, "
            f"marca={self.marca!r}, "
            f"armazenamento_gb={self.armazenamento_gb!r}, "
            f"preco_venda={self.preco_venda!r})"
        )