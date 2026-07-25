from typing import Any

from langchain_core.tools import tool

from crud.estoque import (
    adicionar_ao_estoque,
    atualizar_estoque_minimo,
    buscar_estoque_por_produto_id,
    cadastrar_estoque,
    definir_quantidade_estoque,
    listar_estoques,
    listar_produtos_abaixo_do_minimo,
    listar_produtos_no_limite,
    remover_do_estoque,
)
from database.conexao import SessionLocal


def _estoque_para_dict(
    estoque: Any,
) -> dict[str, Any]:
    """
    Converte um objeto Estoque em um dicionário simples.

    Inclui também informações básicas do produto relacionado,
    quando o relacionamento estiver carregado.
    """

    produto = getattr(estoque, "produto", None)

    return {
        "id": estoque.id,
        "produto_id": estoque.produto_id,
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
        "produto_ativo": (
            produto.ativo
            if produto is not None
            else None
        ),
        "quantidade_atual": estoque.quantidade_atual,
        "estoque_minimo": estoque.estoque_minimo,
        "abaixo_do_minimo": (
            estoque.quantidade_atual
            < estoque.estoque_minimo
        ),
        "no_limite": (
            estoque.quantidade_atual
            == estoque.estoque_minimo
        ),
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza os erros retornados pelas ferramentas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def consultar_estoques(
    apenas_produtos_ativos: bool = True,
) -> dict[str, Any]:
    """
    Lista o estoque dos smartphones cadastrados.

    Use esta ferramenta quando o usuário quiser consultar o estoque
    geral, verificar quantidades disponíveis ou visualizar a situação
    atual dos produtos.

    Por padrão, retorna somente produtos ativos.
    """

    try:
        with SessionLocal() as sessao:
            estoques = listar_estoques(
                sessao=sessao,
                apenas_produtos_ativos=apenas_produtos_ativos,
            )

            return {
                "sucesso": True,
                "quantidade": len(estoques),
                "estoques": [
                    _estoque_para_dict(estoque)
                    for estoque in estoques
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_estoque_produto(
    produto_id: int,
) -> dict[str, Any]:
    """
    Consulta o estoque de um smartphone usando o ID do produto.

    Use quando o usuário informar o ID do produto ou quando outra
    ferramenta já tiver identificado esse ID.
    """

    try:
        with SessionLocal() as sessao:
            estoque = buscar_estoque_por_produto_id(
                sessao=sessao,
                produto_id=produto_id,
            )

            if estoque is None:
                return {
                    "sucesso": False,
                    "erro": (
                        "Estoque do produto com ID "
                        f"{produto_id} não encontrado."
                    ),
                }

            return {
                "sucesso": True,
                "estoque": _estoque_para_dict(estoque),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_produtos_com_estoque_baixo() -> dict[str, Any]:
    """
    Lista os produtos com estoque abaixo do mínimo definido.

    Use quando o usuário quiser identificar produtos que precisam
    de reposição, produtos em situação crítica ou alertas de estoque.
    """

    try:
        with SessionLocal() as sessao:
            estoques = listar_produtos_abaixo_do_minimo(
                sessao=sessao,
            )

            return {
                "sucesso": True,
                "quantidade": len(estoques),
                "estoques": [
                    _estoque_para_dict(estoque)
                    for estoque in estoques
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_produtos_no_estoque_minimo() -> dict[str, Any]:
    """
    Lista os produtos cuja quantidade atual é exatamente igual
    ao estoque mínimo definido.

    Use quando o usuário quiser saber quais produtos estão no limite
    e podem precisar de reposição em breve.
    """

    try:
        with SessionLocal() as sessao:
            estoques = listar_produtos_no_limite(
                sessao=sessao,
            )

            return {
                "sucesso": True,
                "quantidade": len(estoques),
                "estoques": [
                    _estoque_para_dict(estoque)
                    for estoque in estoques
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def criar_estoque_produto(
    produto_id: int,
    quantidade_atual: int = 0,
    estoque_minimo: int = 0,
) -> dict[str, Any]:
    """
    Cria um registro de estoque para um smartphone.

    Use somente quando o produto ainda não possuir estoque cadastrado.
    A quantidade atual e o estoque mínimo não podem ser negativos.
    """

    try:
        with SessionLocal() as sessao:
            try:
                estoque = cadastrar_estoque(
                    sessao=sessao,
                    produto_id=produto_id,
                    quantidade_atual=quantidade_atual,
                    estoque_minimo=estoque_minimo,
                )

                sessao.commit()

                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                if estoque is None:
                    raise RuntimeError(
                        "O estoque foi criado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Estoque cadastrado com sucesso."
                    ),
                    "estoque": _estoque_para_dict(estoque),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def adicionar_unidades_estoque(
    produto_id: int,
    quantidade: int,
) -> dict[str, Any]:
    """
    Adiciona unidades ao estoque atual de um smartphone.

    Use em casos de reposição, recebimento de mercadoria ou entrada
    de novas unidades. A quantidade deve ser maior que zero.
    """

    try:
        with SessionLocal() as sessao:
            try:
                adicionar_ao_estoque(
                    sessao=sessao,
                    produto_id=produto_id,
                    quantidade=quantidade,
                )

                sessao.commit()

                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                if estoque is None:
                    raise RuntimeError(
                        "O estoque foi atualizado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        f"{quantidade} unidade(s) adicionada(s) "
                        "ao estoque."
                    ),
                    "estoque": _estoque_para_dict(estoque),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def remover_unidades_estoque(
    produto_id: int,
    quantidade: int,
) -> dict[str, Any]:
    """
    Remove unidades do estoque de um smartphone.

    Use somente para uma saída manual de estoque. A ferramenta não
    permite que a quantidade do estoque fique negativa.

    Vendas normais devem ser registradas pela ferramenta de vendas,
    pois o CRUD de venda já deve controlar a saída correspondente.
    """

    try:
        with SessionLocal() as sessao:
            try:
                remover_do_estoque(
                    sessao=sessao,
                    produto_id=produto_id,
                    quantidade=quantidade,
                )

                sessao.commit()

                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                if estoque is None:
                    raise RuntimeError(
                        "O estoque foi atualizado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        f"{quantidade} unidade(s) removida(s) "
                        "do estoque."
                    ),
                    "estoque": _estoque_para_dict(estoque),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def definir_quantidade_atual_estoque(
    produto_id: int,
    nova_quantidade: int,
) -> dict[str, Any]:
    """
    Define diretamente a quantidade atual de estoque de um produto.

    Use para correções de inventário ou ajustes manuais. Esta ferramenta
    substitui a quantidade atual pelo valor informado; ela não adiciona
    nem subtrai unidades.
    """

    try:
        with SessionLocal() as sessao:
            try:
                definir_quantidade_estoque(
                    sessao=sessao,
                    produto_id=produto_id,
                    nova_quantidade=nova_quantidade,
                )

                sessao.commit()

                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                if estoque is None:
                    raise RuntimeError(
                        "O estoque foi atualizado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Quantidade atual do estoque "
                        "definida com sucesso."
                    ),
                    "estoque": _estoque_para_dict(estoque),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def definir_estoque_minimo_produto(
    produto_id: int,
    novo_estoque_minimo: int,
) -> dict[str, Any]:
    """
    Atualiza o estoque mínimo de um smartphone.

    Use quando o usuário quiser definir o limite usado para alertas
    de reposição. O estoque mínimo não pode ser negativo.
    """

    try:
        with SessionLocal() as sessao:
            try:
                atualizar_estoque_minimo(
                    sessao=sessao,
                    produto_id=produto_id,
                    novo_estoque_minimo=novo_estoque_minimo,
                )

                sessao.commit()

                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto_id,
                )

                if estoque is None:
                    raise RuntimeError(
                        "O estoque foi atualizado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Estoque mínimo atualizado com sucesso."
                    ),
                    "estoque": _estoque_para_dict(estoque),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_ESTOQUE = [
    consultar_estoques,
    consultar_estoque_produto,
    consultar_produtos_com_estoque_baixo,
    consultar_produtos_no_estoque_minimo,
    criar_estoque_produto,
    adicionar_unidades_estoque,
    remover_unidades_estoque,
    definir_quantidade_atual_estoque,
    definir_estoque_minimo_produto,
]