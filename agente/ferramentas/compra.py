from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool

from crud.compra import (
    atualizar_previsao_entrega,
    atualizar_status_compra,
    buscar_compra_por_id,
    cadastrar_compra,
    listar_compras,
    listar_compras_pendentes,
    listar_compras_por_fornecedor,
    listar_compras_por_produto,
)
from database.conexao import SessionLocal


def _compra_para_dict(
    compra: Any,
) -> dict[str, Any]:
    """
    Converte um objeto Compra em um dicionário serializável.

    Inclui os dados básicos do produto e do fornecedor quando
    os relacionamentos estiverem disponíveis.
    """

    produto = getattr(compra, "produto", None)
    fornecedor = getattr(compra, "fornecedor", None)

    preco_unitario = Decimal(str(compra.preco_unitario))
    valor_total = preco_unitario * compra.quantidade

    return {
        "id": compra.id,
        "produto_id": compra.produto_id,
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
        "fornecedor_id": compra.fornecedor_id,
        "fornecedor_nome": (
            fornecedor.nome
            if fornecedor is not None
            else None
        ),
        "quantidade": compra.quantidade,
        "preco_unitario": float(preco_unitario),
        "valor_total": float(valor_total),
        "data_compra": compra.data_compra.isoformat(),
        "previsao_entrega": compra.previsao_entrega.isoformat(),
        "status": compra.status,
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza os erros retornados pelas ferramentas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


def _converter_data_iso(
    valor: str,
    nome_campo: str,
) -> date:
    """
    Converte uma data no formato AAAA-MM-DD para date.
    """

    try:
        return date.fromisoformat(valor.strip())

    except (ValueError, AttributeError) as erro:
        raise ValueError(
            f"{nome_campo} inválida. "
            "Use o formato AAAA-MM-DD."
        ) from erro


@tool
def consultar_compras(
    status: str | None = None,
) -> dict[str, Any]:
    """
    Lista as compras registradas no banco.

    Pode filtrar pelos status: pendente, enviado, entregue ou
    cancelado. Quando nenhum status for informado, retorna todas
    as compras.
    """

    try:
        with SessionLocal() as sessao:
            compras = listar_compras(
                sessao=sessao,
                status=status,
            )

            return {
                "sucesso": True,
                "filtro_status": status,
                "quantidade": len(compras),
                "compras": [
                    _compra_para_dict(compra)
                    for compra in compras
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_compra_por_id(
    compra_id: int,
) -> dict[str, Any]:
    """
    Busca uma compra pelo seu ID interno.

    Use quando o ID da compra já estiver disponível e forem
    necessários seus dados completos.
    """

    try:
        with SessionLocal() as sessao:
            compra = buscar_compra_por_id(
                sessao=sessao,
                compra_id=compra_id,
            )

            if compra is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Compra com ID {compra_id} "
                        "não encontrada."
                    ),
                }

            return {
                "sucesso": True,
                "compra": _compra_para_dict(compra),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_compras_produto(
    produto_id: int,
) -> dict[str, Any]:
    """
    Lista todas as compras registradas para determinado produto.

    Use para consultar o histórico de aquisição ou reposição
    de um smartphone.
    """

    try:
        with SessionLocal() as sessao:
            compras = listar_compras_por_produto(
                sessao=sessao,
                produto_id=produto_id,
            )

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "quantidade": len(compras),
                "compras": [
                    _compra_para_dict(compra)
                    for compra in compras
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_compras_fornecedor(
    fornecedor_id: int,
) -> dict[str, Any]:
    """
    Lista as compras realizadas com determinado fornecedor.

    Use para consultar o histórico comercial, pedidos ou valores
    comprados de uma empresa fornecedora.
    """

    try:
        with SessionLocal() as sessao:
            compras = listar_compras_por_fornecedor(
                sessao=sessao,
                fornecedor_id=fornecedor_id,
            )

            return {
                "sucesso": True,
                "fornecedor_id": fornecedor_id,
                "quantidade": len(compras),
                "compras": [
                    _compra_para_dict(compra)
                    for compra in compras
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_compras_em_aberto() -> dict[str, Any]:
    """
    Lista as compras que ainda estão pendentes ou em transporte.

    Retorna compras com status pendente ou enviado, ordenadas pela
    previsão de entrega. Use para acompanhar pedidos em aberto.
    """

    try:
        with SessionLocal() as sessao:
            compras = listar_compras_pendentes(
                sessao=sessao,
            )

            return {
                "sucesso": True,
                "quantidade": len(compras),
                "compras": [
                    _compra_para_dict(compra)
                    for compra in compras
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def registrar_compra(
    produto_id: int,
    fornecedor_id: int,
    quantidade: int,
    preco_unitario: float,
    data_compra: str,
    previsao_entrega: str,
    status: str = "pendente",
) -> dict[str, Any]:
    """
    Registra uma nova compra de smartphones junto a um fornecedor.

    As datas devem ser informadas no formato AAAA-MM-DD.
    Os status permitidos são: pendente, enviado, entregue e cancelado.

    Esta ferramenta registra a compra, mas não aumenta
    automaticamente o estoque.
    """

    try:
        try:
            preco_decimal = Decimal(str(preco_unitario))

        except (InvalidOperation, ValueError) as erro:
            raise ValueError(
                "O preço unitário informado não é válido."
            ) from erro

        data_convertida = _converter_data_iso(
            valor=data_compra,
            nome_campo="Data da compra",
        )

        previsao_convertida = _converter_data_iso(
            valor=previsao_entrega,
            nome_campo="Previsão de entrega",
        )

        with SessionLocal() as sessao:
            try:
                compra = cadastrar_compra(
                    sessao=sessao,
                    produto_id=produto_id,
                    fornecedor_id=fornecedor_id,
                    quantidade=quantidade,
                    preco_unitario=preco_decimal,
                    data_compra=data_convertida,
                    previsao_entrega=previsao_convertida,
                    status=status,
                )

                compra_id = compra.id

                sessao.commit()

                compra_salva = buscar_compra_por_id(
                    sessao=sessao,
                    compra_id=compra_id,
                )

                if compra_salva is None:
                    raise RuntimeError(
                        "A compra foi registrada, mas não pôde "
                        "ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Compra registrada com sucesso."
                    ),
                    "compra": _compra_para_dict(compra_salva),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_status_compra(
    compra_id: int,
    novo_status: str,
) -> dict[str, Any]:
    """
    Atualiza o status de uma compra.

    Os status permitidos são: pendente, enviado, entregue e cancelado.

    Alterar o status para entregue não adiciona automaticamente
    unidades ao estoque na implementação atual.
    """

    try:
        with SessionLocal() as sessao:
            try:
                atualizar_status_compra(
                    sessao=sessao,
                    compra_id=compra_id,
                    novo_status=novo_status,
                )

                sessao.commit()

                compra = buscar_compra_por_id(
                    sessao=sessao,
                    compra_id=compra_id,
                )

                if compra is None:
                    raise RuntimeError(
                        "O status foi alterado, mas a compra "
                        "não pôde ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Status da compra atualizado com sucesso."
                    ),
                    "compra": _compra_para_dict(compra),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_previsao_entrega_compra(
    compra_id: int,
    nova_previsao: str,
) -> dict[str, Any]:
    """
    Atualiza a previsão de entrega de uma compra.

    A nova data deve ser informada no formato AAAA-MM-DD e não pode
    ser anterior à data original da compra.
    """

    try:
        previsao_convertida = _converter_data_iso(
            valor=nova_previsao,
            nome_campo="Nova previsão de entrega",
        )

        with SessionLocal() as sessao:
            try:
                atualizar_previsao_entrega(
                    sessao=sessao,
                    compra_id=compra_id,
                    nova_previsao=previsao_convertida,
                )

                sessao.commit()

                compra = buscar_compra_por_id(
                    sessao=sessao,
                    compra_id=compra_id,
                )

                if compra is None:
                    raise RuntimeError(
                        "A previsão foi alterada, mas a compra "
                        "não pôde ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Previsão de entrega atualizada "
                        "com sucesso."
                    ),
                    "compra": _compra_para_dict(compra),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_COMPRA = [
    consultar_compras,
    consultar_compra_por_id,
    consultar_compras_produto,
    consultar_compras_fornecedor,
    consultar_compras_em_aberto,
    registrar_compra,
    modificar_status_compra,
    modificar_previsao_entrega_compra,
]