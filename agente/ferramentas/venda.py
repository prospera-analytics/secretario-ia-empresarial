from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool

from crud.venda import (
    buscar_venda_por_id,
    calcular_faturamento,
    calcular_quantidade_vendida,
    listar_vendas,
    listar_vendas_por_campanha,
    listar_vendas_por_produto,
    produtos_mais_vendidos,
    registrar_venda as registrar_venda_crud,
)
from database.conexao import SessionLocal


def _converter_data_iso(
    valor: str | None,
    nome_campo: str,
) -> date | None:
    """Converte uma string AAAA-MM-DD em date."""

    if valor is None:
        return None

    valor_limpo = valor.strip()

    if not valor_limpo:
        return None

    try:
        return date.fromisoformat(valor_limpo)

    except ValueError as erro:
        raise ValueError(
            f"{nome_campo} inválida. "
            "Use o formato AAAA-MM-DD."
        ) from erro


def _venda_para_dict(
    venda: Any,
) -> dict[str, Any]:
    """Converte uma venda em dicionário serializável."""

    produto = getattr(venda, "produto", None)
    campanha = getattr(venda, "campanha", None)

    preco_unitario = Decimal(
        str(venda.preco_unitario)
    )

    valor_total = (
        preco_unitario * venda.quantidade
    )

    return {
        "id": venda.id,
        "produto_id": venda.produto_id,
        "produto_nome": (
            produto.nome
            if produto is not None
            else None
        ),
        "produto_marca": (
            produto.marca
            if produto is not None
            else None
        ),
        "campanha_id": venda.campanha_id,
        "campanha_nome": (
            getattr(campanha, "nome", None)
            if campanha is not None
            else None
        ),
        "quantidade": venda.quantidade,
        "preco_unitario": float(preco_unitario),
        "valor_total": float(valor_total),
        "data_venda": venda.data_venda.isoformat(),
    }


def _produto_ranking_para_dict(
    produto: Any,
    quantidade_vendida: int,
) -> dict[str, Any]:
    """Converte um produto do ranking em dicionário."""

    return {
        "produto_id": produto.id,
        "nome": produto.nome,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "quantidade_vendida": quantidade_vendida,
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza respostas de erro."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def consultar_vendas(
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, Any]:
    """
    Lista vendas registradas no banco.

    Permite filtrar por período. As datas devem estar no formato
    AAAA-MM-DD.
    """

    try:
        inicio = _converter_data_iso(
            valor=data_inicio,
            nome_campo="Data inicial",
        )

        fim = _converter_data_iso(
            valor=data_fim,
            nome_campo="Data final",
        )

        with SessionLocal() as sessao:
            vendas = listar_vendas(
                sessao=sessao,
                data_inicio=inicio,
                data_fim=fim,
            )

            return {
                "sucesso": True,
                "data_inicio": (
                    inicio.isoformat()
                    if inicio is not None
                    else None
                ),
                "data_fim": (
                    fim.isoformat()
                    if fim is not None
                    else None
                ),
                "quantidade": len(vendas),
                "vendas": [
                    _venda_para_dict(venda)
                    for venda in vendas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_venda_por_id(
    venda_id: int,
) -> dict[str, Any]:
    """Busca uma venda pelo ID."""

    try:
        with SessionLocal() as sessao:
            venda = buscar_venda_por_id(
                sessao=sessao,
                venda_id=venda_id,
            )

            if venda is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Venda com ID {venda_id} "
                        "não encontrada."
                    ),
                }

            return {
                "sucesso": True,
                "venda": _venda_para_dict(venda),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_vendas_produto(
    produto_id: int,
) -> dict[str, Any]:
    """Lista todas as vendas de um produto."""

    try:
        with SessionLocal() as sessao:
            vendas = listar_vendas_por_produto(
                sessao=sessao,
                produto_id=produto_id,
            )

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "quantidade": len(vendas),
                "vendas": [
                    _venda_para_dict(venda)
                    for venda in vendas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_vendas_campanha(
    campanha_id: int,
) -> dict[str, Any]:
    """Lista as vendas associadas a uma campanha."""

    try:
        with SessionLocal() as sessao:
            vendas = listar_vendas_por_campanha(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            return {
                "sucesso": True,
                "campanha_id": campanha_id,
                "quantidade": len(vendas),
                "vendas": [
                    _venda_para_dict(venda)
                    for venda in vendas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def registrar_nova_venda(
    produto_id: int,
    quantidade: int,
    preco_unitario: float,
    data_venda: str,
    campanha_id: int | None = None,
) -> dict[str, Any]:
    """
    Registra uma venda e reduz automaticamente o estoque.

    A data deve estar no formato AAAA-MM-DD. A campanha é opcional.
    """

    try:
        try:
            preco_decimal = Decimal(
                str(preco_unitario)
            )

        except (InvalidOperation, ValueError) as erro:
            raise ValueError(
                "O preço unitário informado não é válido."
            ) from erro

        data_convertida = _converter_data_iso(
            valor=data_venda,
            nome_campo="Data da venda",
        )

        if data_convertida is None:
            raise ValueError(
                "A data da venda é obrigatória."
            )

        with SessionLocal() as sessao:
            try:
                venda = registrar_venda_crud(
                    sessao=sessao,
                    produto_id=produto_id,
                    quantidade=quantidade,
                    preco_unitario=preco_decimal,
                    data_venda=data_convertida,
                    campanha_id=campanha_id,
                )

                venda_id = venda.id

                sessao.commit()

                venda_salva = buscar_venda_por_id(
                    sessao=sessao,
                    venda_id=venda_id,
                )

                if venda_salva is None:
                    raise RuntimeError(
                        "A venda foi registrada, mas não pôde "
                        "ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Venda registrada e estoque atualizado "
                        "com sucesso."
                    ),
                    "venda": _venda_para_dict(
                        venda_salva
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_faturamento(
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, Any]:
    """
    Calcula o faturamento total.

    Pode filtrar por período usando datas no formato AAAA-MM-DD.
    """

    try:
        inicio = _converter_data_iso(
            valor=data_inicio,
            nome_campo="Data inicial",
        )

        fim = _converter_data_iso(
            valor=data_fim,
            nome_campo="Data final",
        )

        with SessionLocal() as sessao:
            faturamento = calcular_faturamento(
                sessao=sessao,
                data_inicio=inicio,
                data_fim=fim,
            )

            return {
                "sucesso": True,
                "data_inicio": (
                    inicio.isoformat()
                    if inicio is not None
                    else None
                ),
                "data_fim": (
                    fim.isoformat()
                    if fim is not None
                    else None
                ),
                "faturamento": float(faturamento),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_quantidade_vendida(
    produto_id: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, Any]:
    """
    Calcula a quantidade total de unidades vendidas.

    Pode filtrar por produto e período.
    """

    try:
        inicio = _converter_data_iso(
            valor=data_inicio,
            nome_campo="Data inicial",
        )

        fim = _converter_data_iso(
            valor=data_fim,
            nome_campo="Data final",
        )

        with SessionLocal() as sessao:
            quantidade = calcular_quantidade_vendida(
                sessao=sessao,
                produto_id=produto_id,
                data_inicio=inicio,
                data_fim=fim,
            )

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "data_inicio": (
                    inicio.isoformat()
                    if inicio is not None
                    else None
                ),
                "data_fim": (
                    fim.isoformat()
                    if fim is not None
                    else None
                ),
                "quantidade_vendida": quantidade,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_produtos_mais_vendidos(
    limite: int = 5,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict[str, Any]:
    """
    Retorna o ranking dos produtos mais vendidos.

    O ranking é baseado na quantidade total de unidades vendidas.
    """

    try:
        inicio = _converter_data_iso(
            valor=data_inicio,
            nome_campo="Data inicial",
        )

        fim = _converter_data_iso(
            valor=data_fim,
            nome_campo="Data final",
        )

        with SessionLocal() as sessao:
            resultados = produtos_mais_vendidos(
                sessao=sessao,
                limite=limite,
                data_inicio=inicio,
                data_fim=fim,
            )

            ranking = [
                {
                    "posicao": posicao,
                    **_produto_ranking_para_dict(
                        produto=produto,
                        quantidade_vendida=quantidade,
                    ),
                }
                for posicao, (
                    produto,
                    quantidade,
                ) in enumerate(
                    resultados,
                    start=1,
                )
            ]

            return {
                "sucesso": True,
                "limite": limite,
                "data_inicio": (
                    inicio.isoformat()
                    if inicio is not None
                    else None
                ),
                "data_fim": (
                    fim.isoformat()
                    if fim is not None
                    else None
                ),
                "quantidade_produtos": len(ranking),
                "produtos": ranking,
            }

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_VENDA = [
    consultar_vendas,
    consultar_venda_por_id,
    consultar_vendas_produto,
    consultar_vendas_campanha,
    registrar_nova_venda,
    consultar_faturamento,
    consultar_quantidade_vendida,
    consultar_produtos_mais_vendidos,
]