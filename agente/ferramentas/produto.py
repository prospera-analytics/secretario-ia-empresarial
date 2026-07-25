from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool

from crud.produto import (
    atualizar_produto,
    buscar_produto_por_id,
    cadastrar_produto,
    desativar_produto,
    listar_produtos,
    pesquisar_produtos,
    reativar_produto,
)
from database.conexao import SessionLocal


def _decimal_para_float(
    valor: Decimal | None,
) -> float | None:
    """Converte Decimal para float para facilitar a serialização."""

    if valor is None:
        return None

    return float(valor)


def _produto_para_dict(
    produto: Any,
) -> dict[str, Any]:
    """Transforma um objeto Produto em um dicionário simples."""

    return {
        "id": produto.id,
        "nome": produto.nome,
        "categoria": produto.categoria,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "descricao": produto.descricao,
        "preco_venda": _decimal_para_float(
            produto.preco_venda
        ),
        "ativo": produto.ativo,
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza erros retornados pelas ferramentas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def consultar_produtos(
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Lista os smartphones cadastrados no banco de dados.

    Use esta ferramenta quando o usuário quiser ver o catálogo,
    conhecer os produtos cadastrados ou listar smartphones.
    Por padrão, retorna somente produtos ativos.
    """

    try:
        with SessionLocal() as sessao:
            produtos = listar_produtos(
                sessao=sessao,
                apenas_ativos=apenas_ativos,
            )

            return {
                "sucesso": True,
                "quantidade": len(produtos),
                "produtos": [
                    _produto_para_dict(produto)
                    for produto in produtos
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_produto_por_id(
    produto_id: int,
) -> dict[str, Any]:
    """
    Busca um smartphone pelo seu ID interno.

    Use esta ferramenta quando o ID do produto já estiver disponível
    e forem necessários seus dados completos.
    """

    try:
        with SessionLocal() as sessao:
            produto = buscar_produto_por_id(
                sessao=sessao,
                produto_id=produto_id,
            )

            if produto is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Produto com ID {produto_id} "
                        "não encontrado."
                    ),
                }

            return {
                "sucesso": True,
                "produto": _produto_para_dict(produto),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def pesquisar_smartphones(
    termo: str,
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Pesquisa smartphones por nome ou marca.

    Use quando o usuário mencionar parte do nome ou da marca,
    como Samsung, Motorola, Apple, iPhone ou Galaxy.
    """

    try:
        with SessionLocal() as sessao:
            produtos = pesquisar_produtos(
                sessao=sessao,
                termo=termo,
                apenas_ativos=apenas_ativos,
            )

            return {
                "sucesso": True,
                "termo": termo,
                "quantidade": len(produtos),
                "produtos": [
                    _produto_para_dict(produto)
                    for produto in produtos
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def criar_produto(
    nome: str,
    marca: str,
    armazenamento_gb: int,
    preco_venda: float,
    descricao: str | None = None,
    categoria: str = "Smartphone",
) -> dict[str, Any]:
    """
    Cadastra um novo smartphone no banco de dados.

    Use somente quando o usuário solicitar explicitamente o cadastro
    de um produto. O preço deve ser informado em reais e o
    armazenamento em gigabytes.
    """

    try:
        preco_decimal = Decimal(str(preco_venda))

    except (InvalidOperation, ValueError):
        return {
            "sucesso": False,
            "erro": "O preço de venda informado não é válido.",
        }

    try:
        with SessionLocal() as sessao:
            try:
                produto = cadastrar_produto(
                    sessao=sessao,
                    nome=nome,
                    marca=marca,
                    armazenamento_gb=armazenamento_gb,
                    preco_venda=preco_decimal,
                    descricao=descricao,
                    categoria=categoria,
                )

                sessao.commit()
                sessao.refresh(produto)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Produto cadastrado com sucesso."
                    ),
                    "produto": _produto_para_dict(produto),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_produto(
    produto_id: int,
    nome: str | None = None,
    marca: str | None = None,
    armazenamento_gb: int | None = None,
    preco_venda: float | None = None,
    descricao: str | None = None,
    categoria: str | None = None,
) -> dict[str, Any]:
    """
    Atualiza um ou mais campos de um smartphone existente.

    Use somente quando o usuário pedir explicitamente uma alteração.
    Informe apenas os campos que realmente devem ser modificados.
    """

    dados: dict[str, Any] = {}

    if nome is not None:
        dados["nome"] = nome

    if marca is not None:
        dados["marca"] = marca

    if armazenamento_gb is not None:
        dados["armazenamento_gb"] = armazenamento_gb

    if preco_venda is not None:
        try:
            dados["preco_venda"] = Decimal(
                str(preco_venda)
            )

        except (InvalidOperation, ValueError):
            return {
                "sucesso": False,
                "erro": (
                    "O preço de venda informado não é válido."
                ),
            }

    if descricao is not None:
        dados["descricao"] = descricao

    if categoria is not None:
        dados["categoria"] = categoria

    if not dados:
        return {
            "sucesso": False,
            "erro": (
                "Nenhum campo foi informado para atualização."
            ),
        }

    try:
        with SessionLocal() as sessao:
            try:
                produto = atualizar_produto(
                    sessao=sessao,
                    produto_id=produto_id,
                    **dados,
                )

                sessao.commit()
                sessao.refresh(produto)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Produto atualizado com sucesso."
                    ),
                    "produto": _produto_para_dict(produto),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def desativar_produto_cadastrado(
    produto_id: int,
) -> dict[str, Any]:
    """
    Desativa um smartphone sem apagar seu histórico.

    Use somente quando o usuário solicitar explicitamente que um
    produto seja desativado ou removido do catálogo ativo.
    """

    try:
        with SessionLocal() as sessao:
            try:
                produto = desativar_produto(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                sessao.commit()
                sessao.refresh(produto)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Produto desativado com sucesso."
                    ),
                    "produto": _produto_para_dict(produto),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def reativar_produto_cadastrado(
    produto_id: int,
) -> dict[str, Any]:
    """
    Reativa um smartphone anteriormente desativado.

    Use somente quando o usuário solicitar explicitamente que o
    produto volte ao catálogo ativo.
    """

    try:
        with SessionLocal() as sessao:
            try:
                produto = reativar_produto(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                sessao.commit()
                sessao.refresh(produto)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Produto reativado com sucesso."
                    ),
                    "produto": _produto_para_dict(produto),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_PRODUTO = [
    consultar_produtos,
    consultar_produto_por_id,
    pesquisar_smartphones,
    criar_produto,
    modificar_produto,
    desativar_produto_cadastrado,
    reativar_produto_cadastrado,
]