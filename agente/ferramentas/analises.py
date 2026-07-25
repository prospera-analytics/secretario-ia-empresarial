from typing import Any

from langchain_core.tools import tool

from analises.margem import (
    analisar_margem_produto,
    listar_analises_margem,
)
from database.conexao import SessionLocal

from analises.estoque import (
    analisar_cobertura_estoque,
    listar_analises_estoque,
)

from analises.fornecedores import (
    recomendar_fornecedor_produto,
)

from analises.alertas import (
    gerar_alertas_empresariais,
    gerar_alertas_produto,
)

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

@tool
def analisar_risco_estoque_produto(
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
) -> dict[str, Any]:
    """
    Analisa velocidade de vendas, dias de cobertura e risco de
    ruptura de estoque para um produto.

    Também sugere uma quantidade de reposição, mas não cria compras
    e não altera o estoque.
    """

    try:
        with SessionLocal() as sessao:
            analise = analisar_cobertura_estoque(
                sessao=sessao,
                produto_id=produto_id,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_alertas_estoque(
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    apenas_ativos: bool = True,
    apenas_com_alerta: bool = True,
) -> dict[str, Any]:
    """
    Analisa o estoque de todos os produtos e lista riscos de ruptura,
    cobertura baixa, estoque mínimo e produtos sem vendas recentes.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            analises = listar_analises_estoque(
                sessao=sessao,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
                apenas_ativos=apenas_ativos,
                apenas_com_alerta=apenas_com_alerta,
            )

            resumo = {
                "critico": sum(
                    item["nivel_alerta"] == "critico"
                    for item in analises
                ),
                "atencao": sum(
                    item["nivel_alerta"] == "atencao"
                    for item in analises
                ),
                "informativo": sum(
                    item["nivel_alerta"] == "informativo"
                    for item in analises
                ),
                "normal": sum(
                    item["nivel_alerta"] == "normal"
                    for item in analises
                ),
            }

            return {
                "sucesso": True,
                "quantidade": len(analises),
                "dias_analise": dias_analise,
                "dias_cobertura_desejada": (
                    dias_cobertura_desejada
                ),
                "apenas_com_alerta": apenas_com_alerta,
                "resumo": resumo,
                "analises": analises,
            }

    except Exception as erro:
        return _resposta_erro(erro)
    
@tool
def recomendar_fornecedor_para_reposicao(
    produto_id: int,
    quantidade: int | None = None,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
) -> dict[str, Any]:
    """
    Recomenda um fornecedor para repor um produto.

    Compara o preço histórico mais recente de cada fornecedor, prazo
    de entrega, risco de ruptura e compras pendentes.

    O preço é apenas uma referência histórica e precisa ser
    confirmado antes da compra.

    Esta ferramenta não registra compras.
    """

    try:
        with SessionLocal() as sessao:
            analise = recomendar_fornecedor_produto(
                sessao=sessao,
                produto_id=produto_id,
                quantidade=quantidade,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(erro)

@tool
def consultar_alertas_produto(
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: float = 10,
    diferenca_concorrente_alerta_percentual: float = 3,
    incluir_informativos: bool = True,
) -> dict[str, Any]:
    """
    Gera todos os alertas empresariais de um produto.

    Verifica estoque, vendas, margem, compras atrasadas,
    concorrência e disponibilidade de fornecedores.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            alertas = gerar_alertas_produto(
                sessao=sessao,
                produto_id=produto_id,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
                diferenca_concorrente_alerta_percentual=(
                    diferenca_concorrente_alerta_percentual
                ),
                incluir_informativos=(
                    incluir_informativos
                ),
            )

            resumo = {
                "critico": sum(
                    alerta["severidade"] == "critico"
                    for alerta in alertas
                ),
                "atencao": sum(
                    alerta["severidade"] == "atencao"
                    for alerta in alertas
                ),
                "informativo": sum(
                    alerta["severidade"] == "informativo"
                    for alerta in alertas
                ),
            }

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "quantidade_alertas": len(
                    alertas
                ),
                "resumo": resumo,
                "alertas": alertas,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_painel_alertas_empresariais(
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: float = 10,
    diferenca_concorrente_alerta_percentual: float = 3,
    apenas_ativos: bool = True,
    incluir_informativos: bool = True,
) -> dict[str, Any]:
    """
    Gera um painel consolidado de alertas empresariais.

    Analisa estoque, vendas, margens, compras atrasadas,
    concorrentes e fornecedores de todos os produtos.

    Use esta ferramenta quando o usuário pedir riscos, problemas,
    prioridades, alertas ou uma visão geral da empresa.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            painel = gerar_alertas_empresariais(
                sessao=sessao,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
                diferenca_concorrente_alerta_percentual=(
                    diferenca_concorrente_alerta_percentual
                ),
                apenas_ativos=apenas_ativos,
                incluir_informativos=(
                    incluir_informativos
                ),
            )

            return {
                "sucesso": True,
                **painel,
            }

    except Exception as erro:
        return _resposta_erro(erro)

FERRAMENTAS_ANALISES = [
    analisar_desconto_produto,
    analisar_descontos_todos_produtos,
    analisar_risco_estoque_produto,
    consultar_alertas_estoque,
    recomendar_fornecedor_para_reposicao,
    consultar_alertas_produto,
    consultar_painel_alertas_empresariais,
]