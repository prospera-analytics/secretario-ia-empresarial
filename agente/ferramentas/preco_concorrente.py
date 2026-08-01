from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool

from crud.concorrente import (
    buscar_menor_preco_concorrente,
    buscar_preco_concorrente_por_id,
    listar_precos_concorrentes,
    listar_precos_por_produto,
    marcar_preco_disponivel,
    marcar_preco_indisponivel,
    registrar_preco_concorrente,
)
from database.conexao import SessionLocal

from servicos.busca_precos import (
    consultar_preco_produto_concorrente,
)

def _converter_decimal(
    valor: float | int | str,
    nome_campo: str,
) -> Decimal:
    """Converte um valor numérico para Decimal."""

    try:
        return Decimal(str(valor))

    except (InvalidOperation, ValueError, TypeError) as erro:
        raise ValueError(
            f"{nome_campo} inválido."
        ) from erro


def _preco_concorrente_para_dict(
    oferta: Any,
) -> dict[str, Any]:
    """Converte uma oferta concorrente em dicionário."""

    produto = getattr(
        oferta,
        "produto",
        None,
    )

    concorrente = getattr(
        oferta,
        "concorrente",
        None,
    )

    preco = Decimal(str(oferta.preco))
    similaridade = Decimal(str(oferta.similaridade))

    preco_interno = None
    diferenca_valor = None
    diferenca_percentual = None

    if produto is not None:
        preco_interno_decimal = Decimal(
            str(produto.preco_venda)
        )

        preco_interno = float(preco_interno_decimal)

    diferenca = (
        preco_interno_decimal
        - preco
    )

    diferenca_valor = float(
        diferenca.quantize(
            Decimal("0.01")
        )
    )

    if preco != 0:
        percentual = (
            diferenca
            / preco
            * Decimal("100")
        )

        diferenca_percentual = float(
            percentual.quantize(
                Decimal("0.01")
            )
        )

    return {
        "id": oferta.id,
        "produto_id": oferta.produto_id,
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
        "armazenamento_gb": (
            produto.armazenamento_gb
            if produto is not None
            else None
        ),
        "preco_interno": preco_interno,
        "concorrente_id": oferta.concorrente_id,
        "concorrente_nome": (
            concorrente.nome
            if concorrente is not None
            else None
        ),
        "concorrente_dominio": (
            concorrente.dominio
            if concorrente is not None
            else None
        ),
        "nome_produto_encontrado": (
            oferta.nome_produto_encontrado
        ),
        "preco": float(preco),
        "moeda": oferta.moeda,
        "diferenca_valor": diferenca_valor,
        "diferenca_percentual": diferenca_percentual,
        "url": oferta.url,
        "similaridade": float(similaridade),
        "tipo_correspondencia": (
            oferta.tipo_correspondencia
        ),
        "disponivel": oferta.disponivel,
        "coletado_em": (
            oferta.coletado_em.isoformat()
            if oferta.coletado_em is not None
            else None
        ),
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza as respostas de erro das ferramentas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def registrar_oferta_concorrente(
    produto_id: int,
    concorrente_id: int,
    nome_produto_encontrado: str,
    preco: float,
    url: str,
    similaridade: float,
    tipo_correspondencia: str,
    moeda: str = "BRL",
    disponivel: bool = True,
) -> dict[str, Any]:
    """
    Registra uma oferta encontrada em um site concorrente.

    A similaridade deve estar entre 0 e 1.

    O tipo de correspondência deve ser:
    - exato: mesmo modelo e configuração;
    - similar: produto comparável, mas não idêntico.
    """

    try:
        preco_decimal = _converter_decimal(
            valor=preco,
            nome_campo="Preço",
        )

        similaridade_decimal = _converter_decimal(
            valor=similaridade,
            nome_campo="Similaridade",
        )

        with SessionLocal() as sessao:
            try:
                oferta = registrar_preco_concorrente(
                    sessao=sessao,
                    produto_id=produto_id,
                    concorrente_id=concorrente_id,
                    nome_produto_encontrado=(
                        nome_produto_encontrado
                    ),
                    preco=preco_decimal,
                    url=url,
                    similaridade=similaridade_decimal,
                    tipo_correspondencia=(
                        tipo_correspondencia
                    ),
                    moeda=moeda,
                    disponivel=disponivel,
                )

                oferta_id = oferta.id

                sessao.commit()

                oferta_salva = (
                    buscar_preco_concorrente_por_id(
                        sessao=sessao,
                        preco_concorrente_id=oferta_id,
                    )
                )

                if oferta_salva is None:
                    raise RuntimeError(
                        "A oferta foi registrada, mas não pôde "
                        "ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Oferta concorrente registrada "
                        "com sucesso."
                    ),
                    "oferta": (
                        _preco_concorrente_para_dict(
                            oferta_salva
                        )
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_oferta_concorrente_por_id(
    preco_concorrente_id: int,
) -> dict[str, Any]:
    """Busca uma oferta concorrente pelo ID."""

    try:
        with SessionLocal() as sessao:
            oferta = buscar_preco_concorrente_por_id(
                sessao=sessao,
                preco_concorrente_id=(
                    preco_concorrente_id
                ),
            )

            if oferta is None:
                return {
                    "sucesso": False,
                    "erro": (
                        "Preço de concorrente com ID "
                        f"{preco_concorrente_id} "
                        "não encontrado."
                    ),
                }

            return {
                "sucesso": True,
                "oferta": _preco_concorrente_para_dict(
                    oferta
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_ofertas_concorrentes(
    produto_id: int | None = None,
    concorrente_id: int | None = None,
    apenas_disponiveis: bool = True,
    tipo_correspondencia: str | None = None,
) -> dict[str, Any]:
    """
    Lista ofertas concorrentes com filtros opcionais.

    É possível filtrar por produto, concorrente,
    disponibilidade e tipo de correspondência.
    """

    try:
        with SessionLocal() as sessao:
            ofertas = listar_precos_concorrentes(
                sessao=sessao,
                produto_id=produto_id,
                concorrente_id=concorrente_id,
                apenas_disponiveis=apenas_disponiveis,
                tipo_correspondencia=(
                    tipo_correspondencia
                ),
            )

            return {
                "sucesso": True,
                "quantidade": len(ofertas),
                "filtros": {
                    "produto_id": produto_id,
                    "concorrente_id": concorrente_id,
                    "apenas_disponiveis": (
                        apenas_disponiveis
                    ),
                    "tipo_correspondencia": (
                        tipo_correspondencia
                    ),
                },
                "ofertas": [
                    _preco_concorrente_para_dict(oferta)
                    for oferta in ofertas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_ofertas_por_produto(
    produto_id: int,
    apenas_disponiveis: bool = True,
) -> dict[str, Any]:
    """
    Lista as ofertas encontradas para determinado produto.

    As ofertas são ordenadas do menor para o maior preço.
    """

    try:
        with SessionLocal() as sessao:
            ofertas = listar_precos_por_produto(
                sessao=sessao,
                produto_id=produto_id,
                apenas_disponiveis=apenas_disponiveis,
            )

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "apenas_disponiveis": (
                    apenas_disponiveis
                ),
                "quantidade": len(ofertas),
                "ofertas": [
                    _preco_concorrente_para_dict(oferta)
                    for oferta in ofertas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_menor_preco_concorrente(
    produto_id: int,
    apenas_correspondencia_exata: bool = False,
) -> dict[str, Any]:
    """
    Busca a oferta disponível de menor preço para um produto.

    Quando apenas_correspondencia_exata=True, ignora ofertas
    classificadas apenas como similares.
    """

    try:
        with SessionLocal() as sessao:
            oferta = buscar_menor_preco_concorrente(
                sessao=sessao,
                produto_id=produto_id,
                apenas_correspondencia_exata=(
                    apenas_correspondencia_exata
                ),
            )

            if oferta is None:
                return {
                    "sucesso": True,
                    "encontrado": False,
                    "mensagem": (
                        "Nenhuma oferta concorrente disponível "
                        "foi encontrada para o produto."
                    ),
                    "oferta": None,
                }

            return {
                "sucesso": True,
                "encontrado": True,
                "oferta": _preco_concorrente_para_dict(
                    oferta
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def marcar_oferta_indisponivel(
    preco_concorrente_id: int,
) -> dict[str, Any]:
    """Marca uma oferta concorrente como indisponível."""

    try:
        with SessionLocal() as sessao:
            try:
                oferta = marcar_preco_indisponivel(
                    sessao=sessao,
                    preco_concorrente_id=(
                        preco_concorrente_id
                    ),
                )

                sessao.commit()

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Oferta marcada como indisponível."
                    ),
                    "oferta": (
                        _preco_concorrente_para_dict(
                            oferta
                        )
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def marcar_oferta_disponivel(
    preco_concorrente_id: int,
) -> dict[str, Any]:
    """Marca novamente uma oferta concorrente como disponível."""

    try:
        with SessionLocal() as sessao:
            try:
                oferta = marcar_preco_disponivel(
                    sessao=sessao,
                    preco_concorrente_id=(
                        preco_concorrente_id
                    ),
                )

                sessao.commit()

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Oferta marcada como disponível."
                    ),
                    "oferta": (
                        _preco_concorrente_para_dict(
                            oferta
                        )
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def buscar_preco_atual_concorrente(
    produto_id: int,
    concorrente_id: int,
    forcar_atualizacao: bool = False,
) -> dict[str, Any]:
    """
    Busca o preço de um produto em um concorrente.

    Primeiro consulta o cache. Quando não houver preço recente,
    pesquisa o site do concorrente com Tavily, extrai a oferta,
    salva o resultado no banco e retorna a URL real da página.

    Use forcar_atualizacao=True quando o usuário pedir explicitamente
    uma atualização ou um preço novo.
    """

    try:
        with SessionLocal() as sessao:
            try:
                resultado = consultar_preco_produto_concorrente(
                    sessao=sessao,
                    produto_id=produto_id,
                    concorrente_id=concorrente_id,
                    forcar_atualizacao=forcar_atualizacao,
                )

                if resultado is None:
                    return {
                        "sucesso": True,
                        "encontrado": False,
                        "mensagem": (
                            "Não foi encontrada uma oferta concorrente "
                            "verificável para esse produto."
                        ),
                    }

                sessao.commit()

                return {
                    "sucesso": True,
                    "encontrado": True,
                    "fonte": resultado.fonte,
                    "produto_id": resultado.produto_id,
                    "produto_nome": resultado.produto_nome,
                    "concorrente_id": resultado.concorrente_id,
                    "concorrente_nome": resultado.concorrente_nome,
                    "produto_encontrado": resultado.titulo_encontrado,
                    "preco": float(resultado.preco),
                    "moeda": resultado.moeda,
                    "correspondencia": (
                        resultado.tipo_correspondencia
                    ),
                    "similaridade": float(
                        resultado.similaridade
                    ),
                    "url": resultado.url,
                    "coletado_em": (
                        resultado.coletado_em.isoformat()
                        if resultado.coletado_em is not None
                        else None
                    ),
                    "diferencas": list(
                        resultado.diferencas
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_PRECO_CONCORRENTE = [
    buscar_preco_atual_concorrente,
    registrar_oferta_concorrente,
    consultar_oferta_concorrente_por_id,
    consultar_ofertas_concorrentes,
    consultar_ofertas_por_produto,
    consultar_menor_preco_concorrente,
    marcar_oferta_indisponivel,
    marcar_oferta_disponivel,
]