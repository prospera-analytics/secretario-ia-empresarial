from typing import Any

from langchain_core.tools import tool

from analises.margem import (
    analisar_margem_produto,
    listar_analises_margem,
)
from database.conexao import SessionLocal


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza erros das ferramentas analíticas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def analisar_desconto_produto(
    produto_id: int,
    desconto_percentual: float = 0,
    margem_minima_percentual: float = 10,
) -> dict[str, Any]:
    """
    Analisa se um desconto é financeiramente seguro para um produto.

    Calcula preço final, lucro unitário, margem resultante, desconto
    máximo sem prejuízo e desconto máximo preservando a margem mínima.

    Esta ferramenta apenas analisa. Ela não altera o preço do produto
    e não aplica o desconto.
    """

    try:
        with SessionLocal() as sessao:
            analise = analisar_margem_produto(
                sessao=sessao,
                produto_id=produto_id,
                desconto_percentual=desconto_percentual,
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def analisar_descontos_todos_produtos(
    desconto_percentual: float = 0,
    margem_minima_percentual: float = 10,
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Analisa o impacto de um desconto em todos os produtos.

    Identifica produtos que ficariam com prejuízo, margem baixa ou
    desconto financeiramente seguro.

    Esta ferramenta não altera preços nem aplica descontos.
    """

    try:
        with SessionLocal() as sessao:
            analises = listar_analises_margem(
                sessao=sessao,
                desconto_percentual=desconto_percentual,
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
                apenas_ativos=apenas_ativos,
            )

            resumo = {
                "prejuizo": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "prejuizo"
                ),
                "margem_baixa": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "margem_baixa"
                ),
                "desconto_seguro": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "desconto_seguro"
                ),
                "sem_custo_referencia": sum(
                    1
                    for item in analises
                    if not item.get(
                        "possui_custo_referencia",
                        False,
                    )
                ),
            }

            return {
                "sucesso": True,
                "desconto_analisado_percentual": (
                    desconto_percentual
                ),
                "margem_minima_percentual": (
                    margem_minima_percentual
                ),
                "quantidade_produtos": len(
                    analises
                ),
                "resumo": resumo,
                "analises": analises,
            }

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_ANALISES = [
    analisar_desconto_produto,
    analisar_descontos_todos_produtos,
]