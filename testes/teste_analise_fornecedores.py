from sqlalchemy import select

from agente.ferramentas.analises import (
    recomendar_fornecedor_para_reposicao,
)
from database.conexao import SessionLocal
from database.models.compra import Compra
from database.models.estoque import Estoque
from database.models.fornecedor import Fornecedor
from database.models.produto import Produto


def localizar_produto_valido() -> int:
    """
    Localiza um produto ativo que possua estoque e histórico
    de compra com fornecedor ativo.
    """

    with SessionLocal() as sessao:
        consulta = (
            select(Produto.id)
            .join(
                Estoque,
                Estoque.produto_id == Produto.id,
            )
            .join(
                Compra,
                Compra.produto_id == Produto.id,
            )
            .join(
                Fornecedor,
                Fornecedor.id == Compra.fornecedor_id,
            )
            .where(
                Produto.ativo.is_(True),
                Fornecedor.ativo.is_(True),
                Compra.status != "cancelada",
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
                "Nenhum produto com estoque, fornecedor ativo "
                "e compra válida foi encontrado."
            )

        return produto_id


def testar_recomendacao_fornecedor() -> None:
    """Testa a recomendação de fornecedor para reposição."""

    produto_id = localizar_produto_valido()

    resultado = (
        recomendar_fornecedor_para_reposicao.invoke(
            {
                "produto_id": produto_id,
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
            }
        )
    )

    print("\nRecomendação automática:")
    print(resultado)

    assert resultado["sucesso"] is True

    analise = resultado["analise"]

    assert analise["produto_id"] == produto_id
    assert (
        analise["possui_fornecedores_historicos"]
        is True
    )

    assert (
        analise["quantidade_a_comprar_apos_pendencias"]
        >= 0
    )

    assert len(
        analise["comparacao_fornecedores"]
    ) > 0

    melhor = analise["melhor_fornecedor"]

    assert melhor["fornecedor_id"] > 0
    assert melhor["preco_historico_referencia"] > 0
    assert melhor["prazo_entrega_dias"] >= 0
    assert melhor["custo_total_estimado"] >= 0

    resultado_quantidade_manual = (
        recomendar_fornecedor_para_reposicao.invoke(
            {
                "produto_id": produto_id,
                "quantidade": 10,
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
            }
        )
    )

    print("\nRecomendação para 10 unidades:")
    print(resultado_quantidade_manual)

    assert (
        resultado_quantidade_manual["sucesso"]
        is True
    )

    analise_manual = (
        resultado_quantidade_manual["analise"]
    )

    assert (
        analise_manual[
            "quantidade_reposicao_original"
        ]
        == 10
    )

    print(
        "\nTodos os testes da análise de fornecedores passaram."
    )


if __name__ == "__main__":
    testar_recomendacao_fornecedor()