from sqlalchemy import select

from agente.ferramentas.analises import (
    analisar_risco_estoque_produto,
    consultar_alertas_estoque,
)
from database.conexao import SessionLocal
from database.models.estoque import Estoque
from database.models.produto import Produto


def localizar_produto_com_estoque() -> int:
    """Localiza um produto ativo com estoque cadastrado."""

    with SessionLocal() as sessao:
        consulta = (
            select(Produto.id)
            .join(
                Estoque,
                Estoque.produto_id == Produto.id,
            )
            .where(
                Produto.ativo.is_(True)
            )
            .order_by(
                Produto.id.asc()
            )
            .limit(1)
        )

        produto_id = sessao.scalar(
            consulta
        )

        if produto_id is None:
            raise RuntimeError(
                "Nenhum produto ativo com estoque cadastrado "
                "foi encontrado."
            )

        return produto_id


def testar_analise_estoque() -> None:
    """Testa análises de cobertura e alertas de estoque."""

    produto_id = localizar_produto_com_estoque()

    resultado_produto = (
        analisar_risco_estoque_produto.invoke(
            {
                "produto_id": produto_id,
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
            }
        )
    )

    print("\nAnálise de estoque do produto:")
    print(resultado_produto)

    assert resultado_produto["sucesso"] is True

    analise = resultado_produto["analise"]

    assert analise["produto_id"] == produto_id
    assert analise["possui_estoque_cadastrado"] is True
    assert analise["quantidade_atual"] >= 0
    assert analise["estoque_minimo"] >= 0
    assert analise["unidades_vendidas_periodo"] >= 0
    assert analise["media_vendas_diaria"] >= 0

    assert analise["nivel_alerta"] in {
        "critico",
        "atencao",
        "informativo",
        "normal",
    }

    assert (
        analise["quantidade_reposicao_sugerida"]
        >= 0
    )

    resultado_todos = (
        consultar_alertas_estoque.invoke(
            {
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
                "apenas_ativos": True,
                "apenas_com_alerta": False,
            }
        )
    )

    print("\nAnálise de todos os estoques:")
    print(resultado_todos)

    assert resultado_todos["sucesso"] is True
    assert resultado_todos["quantidade"] > 0

    total_resumo = sum(
        resultado_todos["resumo"].values()
    )

    assert (
        total_resumo
        == resultado_todos["quantidade"]
    )

    resultado_alertas = (
        consultar_alertas_estoque.invoke(
            {
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
                "apenas_ativos": True,
                "apenas_com_alerta": True,
            }
        )
    )

    print("\nSomente alertas de estoque:")
    print(resultado_alertas)

    assert resultado_alertas["sucesso"] is True

    for item in resultado_alertas["analises"]:
        assert item["nivel_alerta"] in {
            "critico",
            "atencao",
        }

    print(
        "\nTodos os testes da análise de estoque passaram."
    )


if __name__ == "__main__":
    testar_analise_estoque()