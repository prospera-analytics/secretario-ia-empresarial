from langchain_core.tools import BaseTool

from agente.ferramentas.campanha import (
    FERRAMENTAS_CAMPANHA,
)
from agente.ferramentas.compra import (
    FERRAMENTAS_COMPRA,
)
from agente.ferramentas.concorrente import (
    FERRAMENTAS_CONCORRENTE,
)
from agente.ferramentas.estoque import (
    FERRAMENTAS_ESTOQUE,
)
from agente.ferramentas.fornecedor import (
    FERRAMENTAS_FORNECEDOR,
)
from agente.ferramentas.preco_concorrente import (
    FERRAMENTAS_PRECO_CONCORRENTE,
)
from agente.ferramentas.produto import (
    FERRAMENTAS_PRODUTO,
)
from agente.ferramentas.venda import (
    FERRAMENTAS_VENDA,
)

from agente.ferramentas.analises import (
    FERRAMENTAS_ANALISES,
)


def criar_ferramentas() -> list[BaseTool]:
    """
    Cria a lista completa de ferramentas disponíveis para o agente.

    Cada grupo representa uma área operacional da empresa:
    produtos, estoque, fornecedores, compras, vendas, campanhas
    e monitoramento de concorrentes.
    """

    ferramentas: list[BaseTool] = [
        *FERRAMENTAS_PRODUTO,
        *FERRAMENTAS_ESTOQUE,
        *FERRAMENTAS_FORNECEDOR,
        *FERRAMENTAS_COMPRA,
        *FERRAMENTAS_VENDA,
        *FERRAMENTAS_CAMPANHA,
        *FERRAMENTAS_CONCORRENTE,
        *FERRAMENTAS_PRECO_CONCORRENTE,
        *FERRAMENTAS_ANALISES,
    ]

    return ferramentas


__all__ = [
    "criar_ferramentas",
]