from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from crud.estoque import remover_do_estoque
from database.models.campanha import Campanha
from database.models.produto import Produto
from database.models.venda import Venda


def listar_vendas(
    sessao: Session,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[Venda]:
    """Lista vendas com produto e campanha carregados."""

    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    consulta = (
        select(Venda)
        .options(
            joinedload(Venda.produto),
            joinedload(Venda.campanha),
        )
        .order_by(Venda.data_venda.desc(), Venda.id.desc())
    )

    if data_inicio is not None:
        consulta = consulta.where(
            Venda.data_venda >= data_inicio
        )

    if data_fim is not None:
        consulta = consulta.where(
            Venda.data_venda <= data_fim
        )

    return list(sessao.scalars(consulta).all())


def buscar_venda_por_id(
    sessao: Session,
    venda_id: int,
) -> Venda | None:
    """Busca uma venda pelo ID."""

    consulta = (
        select(Venda)
        .options(
            joinedload(Venda.produto),
            joinedload(Venda.campanha),
        )
        .where(Venda.id == venda_id)
    )

    return sessao.scalar(consulta)


def listar_vendas_por_produto(
    sessao: Session,
    produto_id: int,
) -> list[Venda]:
    """Lista todas as vendas de um produto."""

    consulta = (
        select(Venda)
        .options(
            joinedload(Venda.produto),
            joinedload(Venda.campanha),
        )
        .where(Venda.produto_id == produto_id)
        .order_by(
            Venda.data_venda.desc(),
            Venda.id.desc(),
        )
    )

    return list(sessao.scalars(consulta).all())


def listar_vendas_por_campanha(
    sessao: Session,
    campanha_id: int,
) -> list[Venda]:
    """Lista as vendas associadas a uma campanha."""

    consulta = (
        select(Venda)
        .options(
            joinedload(Venda.produto),
            joinedload(Venda.campanha),
        )
        .where(Venda.campanha_id == campanha_id)
        .order_by(
            Venda.data_venda.desc(),
            Venda.id.desc(),
        )
    )

    return list(sessao.scalars(consulta).all())


def registrar_venda(
    sessao: Session,
    produto_id: int,
    quantidade: int,
    preco_unitario: Decimal,
    data_venda: date,
    campanha_id: int | None = None,
) -> Venda:
    """
    Registra uma venda e remove a quantidade correspondente do estoque.

    O commit deve ser controlado por quem chamou a função.
    """

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    if not produto.ativo:
        raise ValueError(
            f"O produto '{produto.nome}' está desativado."
        )

    if quantidade <= 0:
        raise ValueError(
            "A quantidade vendida deve ser maior que zero."
        )

    preco = Decimal(str(preco_unitario))

    if preco <= 0:
        raise ValueError(
            "O preço unitário deve ser maior que zero."
        )

    if campanha_id is not None:
        campanha = sessao.get(Campanha, campanha_id)

        if campanha is None:
            raise ValueError(
                f"Campanha com ID {campanha_id} não encontrada."
            )

        if not (
            campanha.data_inicio
            <= data_venda
            <= campanha.data_fim
        ):
            raise ValueError(
                "A data da venda está fora do período da campanha."
            )

    remover_do_estoque(
        sessao=sessao,
        produto_id=produto_id,
        quantidade=quantidade,
    )

    venda = Venda(
        produto_id=produto_id,
        campanha_id=campanha_id,
        quantidade=quantidade,
        preco_unitario=preco,
        data_venda=data_venda,
    )

    sessao.add(venda)
    sessao.flush()
    sessao.refresh(venda)

    return venda


def calcular_valor_total(
    venda: Venda,
) -> Decimal:
    """Calcula o valor total de uma venda."""

    return (
        Decimal(str(venda.preco_unitario))
        * venda.quantidade
    )


def calcular_faturamento(
    sessao: Session,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> Decimal:
    """Calcula o faturamento total no período informado."""

    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    consulta = select(
        func.coalesce(
            func.sum(
                Venda.quantidade * Venda.preco_unitario
            ),
            0,
        )
    )

    if data_inicio is not None:
        consulta = consulta.where(
            Venda.data_venda >= data_inicio
        )

    if data_fim is not None:
        consulta = consulta.where(
            Venda.data_venda <= data_fim
        )

    resultado = sessao.scalar(consulta)

    return Decimal(str(resultado))


def calcular_quantidade_vendida(
    sessao: Session,
    produto_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> int:
    """Calcula a quantidade de unidades vendidas."""

    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    consulta = select(
        func.coalesce(
            func.sum(Venda.quantidade),
            0,
        )
    )

    if produto_id is not None:
        consulta = consulta.where(
            Venda.produto_id == produto_id
        )

    if data_inicio is not None:
        consulta = consulta.where(
            Venda.data_venda >= data_inicio
        )

    if data_fim is not None:
        consulta = consulta.where(
            Venda.data_venda <= data_fim
        )

    resultado = sessao.scalar(consulta)

    return int(resultado or 0)


def produtos_mais_vendidos(
    sessao: Session,
    limite: int = 5,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[tuple[Produto, int]]:
    """Retorna os produtos mais vendidos por quantidade."""

    if limite <= 0:
        raise ValueError(
            "O limite deve ser maior que zero."
        )

    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    consulta = (
        select(
            Produto,
            func.sum(Venda.quantidade).label(
                "quantidade_vendida"
            ),
        )
        .join(
            Venda,
            Venda.produto_id == Produto.id,
        )
        .group_by(Produto.id)
        .order_by(
            func.sum(Venda.quantidade).desc(),
            Produto.nome.asc(),
        )
        .limit(limite)
    )

    if data_inicio is not None:
        consulta = consulta.where(
            Venda.data_venda >= data_inicio
        )

    if data_fim is not None:
        consulta = consulta.where(
            Venda.data_venda <= data_fim
        )

    resultados = sessao.execute(consulta).all()

    return [
        (produto, int(quantidade))
        for produto, quantidade in resultados
    ]