from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.models.compra import Compra
from database.models.fornecedor import Fornecedor
from database.models.produto import Produto


STATUS_VALIDOS = {
    "pendente",
    "enviado",
    "entregue",
    "cancelado",
}


def listar_compras(
    sessao: Session,
    status: str | None = None,
) -> list[Compra]:
    """Lista compras com produto e fornecedor carregados."""

    consulta = (
        select(Compra)
        .options(
            joinedload(Compra.produto),
            joinedload(Compra.fornecedor),
        )
        .order_by(Compra.data_compra.desc(), Compra.id.desc())
    )

    if status is not None:
        status_limpo = status.strip().lower()

        if status_limpo not in STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Valores permitidos: "
                + ", ".join(sorted(STATUS_VALIDOS))
            )

        consulta = consulta.where(Compra.status == status_limpo)

    return list(sessao.scalars(consulta).all())


def buscar_compra_por_id(
    sessao: Session,
    compra_id: int,
) -> Compra | None:
    """Busca uma compra pelo ID."""

    consulta = (
        select(Compra)
        .options(
            joinedload(Compra.produto),
            joinedload(Compra.fornecedor),
        )
        .where(Compra.id == compra_id)
    )

    return sessao.scalar(consulta)


def listar_compras_por_produto(
    sessao: Session,
    produto_id: int,
) -> list[Compra]:
    """Lista as compras de um produto."""

    consulta = (
        select(Compra)
        .options(
            joinedload(Compra.produto),
            joinedload(Compra.fornecedor),
        )
        .where(Compra.produto_id == produto_id)
        .order_by(Compra.data_compra.desc())
    )

    return list(sessao.scalars(consulta).all())


def listar_compras_por_fornecedor(
    sessao: Session,
    fornecedor_id: int,
) -> list[Compra]:
    """Lista as compras realizadas com um fornecedor."""

    consulta = (
        select(Compra)
        .options(
            joinedload(Compra.produto),
            joinedload(Compra.fornecedor),
        )
        .where(Compra.fornecedor_id == fornecedor_id)
        .order_by(Compra.data_compra.desc())
    )

    return list(sessao.scalars(consulta).all())


def listar_compras_pendentes(
    sessao: Session,
) -> list[Compra]:
    """Lista compras que ainda não foram entregues."""

    consulta = (
        select(Compra)
        .options(
            joinedload(Compra.produto),
            joinedload(Compra.fornecedor),
        )
        .where(Compra.status.in_(["pendente", "enviado"]))
        .order_by(
            Compra.previsao_entrega.asc(),
            Compra.data_compra.asc(),
        )
    )

    return list(sessao.scalars(consulta).all())


def cadastrar_compra(
    sessao: Session,
    produto_id: int,
    fornecedor_id: int,
    quantidade: int,
    preco_unitario: Decimal,
    data_compra: date,
    previsao_entrega: date,
    status: str = "pendente",
) -> Compra:
    """Cadastra uma compra de produtos."""

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    fornecedor = sessao.get(Fornecedor, fornecedor_id)

    if fornecedor is None:
        raise ValueError(
            f"Fornecedor com ID {fornecedor_id} não encontrado."
        )

    if not produto.ativo:
        raise ValueError(
            f"O produto '{produto.nome}' está desativado."
        )

    if not fornecedor.ativo:
        raise ValueError(
            f"O fornecedor '{fornecedor.nome}' está desativado."
        )

    if quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    preco = Decimal(str(preco_unitario))

    if preco <= 0:
        raise ValueError(
            "O preço unitário deve ser maior que zero."
        )

    if previsao_entrega < data_compra:
        raise ValueError(
            "A previsão de entrega não pode ser anterior "
            "à data da compra."
        )

    status_limpo = status.strip().lower()

    if status_limpo not in STATUS_VALIDOS:
        raise ValueError(
            "Status inválido. Valores permitidos: "
            + ", ".join(sorted(STATUS_VALIDOS))
        )

    compra = Compra(
        produto_id=produto_id,
        fornecedor_id=fornecedor_id,
        quantidade=quantidade,
        preco_unitario=preco,
        data_compra=data_compra,
        previsao_entrega=previsao_entrega,
        status=status_limpo,
    )

    sessao.add(compra)
    sessao.flush()
    sessao.refresh(compra)

    return compra


def atualizar_status_compra(
    sessao: Session,
    compra_id: int,
    novo_status: str,
) -> Compra:
    """Atualiza o status de uma compra."""

    compra = buscar_compra_por_id(
        sessao=sessao,
        compra_id=compra_id,
    )

    if compra is None:
        raise ValueError(
            f"Compra com ID {compra_id} não encontrada."
        )

    status_limpo = novo_status.strip().lower()

    if status_limpo not in STATUS_VALIDOS:
        raise ValueError(
            "Status inválido. Valores permitidos: "
            + ", ".join(sorted(STATUS_VALIDOS))
        )

    compra.status = status_limpo

    sessao.flush()
    sessao.refresh(compra)

    return compra


def atualizar_previsao_entrega(
    sessao: Session,
    compra_id: int,
    nova_previsao: date,
) -> Compra:
    """Atualiza a previsão de entrega."""

    compra = buscar_compra_por_id(
        sessao=sessao,
        compra_id=compra_id,
    )

    if compra is None:
        raise ValueError(
            f"Compra com ID {compra_id} não encontrada."
        )

    if nova_previsao < compra.data_compra:
        raise ValueError(
            "A previsão de entrega não pode ser anterior "
            "à data da compra."
        )

    compra.previsao_entrega = nova_previsao

    sessao.flush()
    sessao.refresh(compra)

    return compra


def calcular_valor_total(compra: Compra) -> Decimal:
    """Calcula o valor total de uma compra."""

    return Decimal(compra.preco_unitario) * compra.quantidade