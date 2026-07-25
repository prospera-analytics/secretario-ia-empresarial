from typing import Any

from langchain_core.tools import tool

from crud.fornecedor import (
    atualizar_fornecedor,
    buscar_fornecedor_por_id,
    cadastrar_fornecedor,
    desativar_fornecedor,
    listar_fornecedores,
    pesquisar_fornecedores,
    reativar_fornecedor,
)
from database.conexao import SessionLocal


def _fornecedor_para_dict(
    fornecedor: Any,
) -> dict[str, Any]:
    """Converte um objeto Fornecedor em um dicionário simples."""

    return {
        "id": fornecedor.id,
        "nome": fornecedor.nome,
        "cidade": fornecedor.cidade,
        "estado": fornecedor.estado,
        "prazo_entrega_dias": fornecedor.prazo_entrega_dias,
        "ativo": fornecedor.ativo,
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
def consultar_fornecedores(
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Lista os fornecedores cadastrados no banco de dados.

    Use quando o usuário quiser consultar fornecedores, verificar
    opções de fornecimento ou visualizar empresas fornecedoras.

    Por padrão, retorna somente fornecedores ativos.
    """

    try:
        with SessionLocal() as sessao:
            fornecedores = listar_fornecedores(
                sessao=sessao,
                apenas_ativos=apenas_ativos,
            )

            return {
                "sucesso": True,
                "quantidade": len(fornecedores),
                "fornecedores": [
                    _fornecedor_para_dict(fornecedor)
                    for fornecedor in fornecedores
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_fornecedor_por_id(
    fornecedor_id: int,
) -> dict[str, Any]:
    """
    Busca um fornecedor pelo seu ID interno.

    Use quando o ID do fornecedor já estiver disponível e forem
    necessários seus dados completos.
    """

    try:
        with SessionLocal() as sessao:
            fornecedor = buscar_fornecedor_por_id(
                sessao=sessao,
                fornecedor_id=fornecedor_id,
            )

            if fornecedor is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Fornecedor com ID {fornecedor_id} "
                        "não encontrado."
                    ),
                }

            return {
                "sucesso": True,
                "fornecedor": _fornecedor_para_dict(fornecedor),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def pesquisar_fornecedores_cadastrados(
    termo: str,
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Pesquisa fornecedores por nome, cidade ou estado.

    Use quando o usuário informar apenas parte do nome, uma cidade
    ou uma sigla estadual, como São Paulo, Campinas ou SP.
    """

    try:
        with SessionLocal() as sessao:
            fornecedores = pesquisar_fornecedores(
                sessao=sessao,
                termo=termo,
                apenas_ativos=apenas_ativos,
            )

            return {
                "sucesso": True,
                "termo": termo,
                "quantidade": len(fornecedores),
                "fornecedores": [
                    _fornecedor_para_dict(fornecedor)
                    for fornecedor in fornecedores
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def criar_fornecedor(
    nome: str,
    cidade: str,
    estado: str,
    prazo_entrega_dias: int,
) -> dict[str, Any]:
    """
    Cadastra um novo fornecedor.

    Use somente quando o usuário solicitar explicitamente o cadastro
    de um fornecedor. O estado deve ser informado com duas letras,
    como SP, RJ ou MG.
    """

    try:
        with SessionLocal() as sessao:
            try:
                fornecedor = cadastrar_fornecedor(
                    sessao=sessao,
                    nome=nome,
                    cidade=cidade,
                    estado=estado,
                    prazo_entrega_dias=prazo_entrega_dias,
                )

                sessao.commit()
                sessao.refresh(fornecedor)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Fornecedor cadastrado com sucesso."
                    ),
                    "fornecedor": _fornecedor_para_dict(
                        fornecedor
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_fornecedor(
    fornecedor_id: int,
    nome: str | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    prazo_entrega_dias: int | None = None,
) -> dict[str, Any]:
    """
    Atualiza um ou mais campos de um fornecedor.

    Use somente quando o usuário solicitar explicitamente uma
    alteração. Informe apenas os campos que devem ser modificados.
    """

    dados: dict[str, Any] = {}

    if nome is not None:
        dados["nome"] = nome

    if cidade is not None:
        dados["cidade"] = cidade

    if estado is not None:
        dados["estado"] = estado

    if prazo_entrega_dias is not None:
        dados["prazo_entrega_dias"] = prazo_entrega_dias

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
                fornecedor = atualizar_fornecedor(
                    sessao=sessao,
                    fornecedor_id=fornecedor_id,
                    **dados,
                )

                sessao.commit()
                sessao.refresh(fornecedor)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Fornecedor atualizado com sucesso."
                    ),
                    "fornecedor": _fornecedor_para_dict(
                        fornecedor
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def desativar_fornecedor_cadastrado(
    fornecedor_id: int,
) -> dict[str, Any]:
    """
    Desativa um fornecedor sem apagar seu histórico.

    Use somente quando o usuário pedir explicitamente a desativação
    ou remoção do fornecedor da lista de fornecedores ativos.
    """

    try:
        with SessionLocal() as sessao:
            try:
                fornecedor = desativar_fornecedor(
                    sessao=sessao,
                    fornecedor_id=fornecedor_id,
                )

                sessao.commit()
                sessao.refresh(fornecedor)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Fornecedor desativado com sucesso."
                    ),
                    "fornecedor": _fornecedor_para_dict(
                        fornecedor
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def reativar_fornecedor_cadastrado(
    fornecedor_id: int,
) -> dict[str, Any]:
    """
    Reativa um fornecedor anteriormente desativado.

    Use quando o usuário solicitar explicitamente que o fornecedor
    volte a ficar disponível para novas operações.
    """

    try:
        with SessionLocal() as sessao:
            try:
                fornecedor = reativar_fornecedor(
                    sessao=sessao,
                    fornecedor_id=fornecedor_id,
                )

                sessao.commit()
                sessao.refresh(fornecedor)

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Fornecedor reativado com sucesso."
                    ),
                    "fornecedor": _fornecedor_para_dict(
                        fornecedor
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_FORNECEDOR = [
    consultar_fornecedores,
    consultar_fornecedor_por_id,
    pesquisar_fornecedores_cadastrados,
    criar_fornecedor,
    modificar_fornecedor,
    desativar_fornecedor_cadastrado,
    reativar_fornecedor_cadastrado,
]