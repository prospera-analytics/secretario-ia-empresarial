from sqlalchemy import select

from agente.ferramentas.analises import (
    analisar_desconto_produto,
    analisar_descontos_todos_produtos,
)
from database.conexao import SessionLocal
from database.models.compra import Compra
from database.models.produto import Produto


def localizar_produto_com_compra() -> Produto:
    """Localiza um produto ativo que possua compra não cancelada."""

    with SessionLocal() as sessao:
        consulta = (
            select(Produto)
            .join(
                Compra,
                Compra.produto_id == Produto.id,
            )
            .where(
                Produto.ativo.is_(True),
                Compra.status != "cancelada",
            )
            .order_by(
                Produto.id.asc(),
                Compra.data_compra.desc(),
            )
            .limit(1)
        )

        produto = sessao.scalar(
            consulta
        )

        if produto is None:
            raise RuntimeError(
                "Nenhum produto ativo com compra válida foi "
                "encontrado para executar o teste."
            )

        produto_id = produto.id
        produto_nome = produto.nome

    produto_teste = Produto(
        id=produto_id,
        nome=produto_nome,
        categoria="Smartphone",
        marca="Teste",
        armazenamento_gb=1,
        preco_venda=1,
        ativo=True,
    )

    return produto_teste


def testar_analise_margem() -> None:
    """Testa as ferramentas de margem e desconto."""

    produto = localizar_produto_com_compra()

    resultado_sem_desconto = (
        analisar_desconto_produto.invoke(
            {
                "produto_id": produto.id,
                "desconto_percentual": 0,
                "margem_minima_percentual": 10,
            }
        )
    )

    print("\nAnálise sem desconto:")
    print(resultado_sem_desconto)

    assert resultado_sem_desconto["sucesso"] is True

    analise_sem_desconto = (
        resultado_sem_desconto["analise"]
    )

    assert (
        analise_sem_desconto[
            "possui_custo_referencia"
        ]
        is True
    )

    assert (
        analise_sem_desconto[
            "preco_com_desconto"
        ]
        == analise_sem_desconto[
            "preco_venda_atual"
        ]
    )

    assert (
        analise_sem_desconto[
            "lucro_unitario_com_desconto"
        ]
        == analise_sem_desconto[
            "lucro_unitario_atual"
        ]
    )

    resultado_desconto_moderado = (
        analisar_desconto_produto.invoke(
            {
                "produto_id": produto.id,
                "desconto_percentual": 5,
                "margem_minima_percentual": 10,
            }
        )
    )

    print("\nAnálise com desconto de 5%:")
    print(resultado_desconto_moderado)

    assert (
        resultado_desconto_moderado["sucesso"]
        is True
    )

    analise_moderada = (
        resultado_desconto_moderado["analise"]
    )

    assert (
        analise_moderada["preco_com_desconto"]
        < analise_moderada["preco_venda_atual"]
    )

    assert (
        analise_moderada[
            "lucro_unitario_com_desconto"
        ]
        < analise_moderada[
            "lucro_unitario_atual"
        ]
    )

    resultado_desconto_extremo = (
        analisar_desconto_produto.invoke(
            {
                "produto_id": produto.id,
                "desconto_percentual": 99,
                "margem_minima_percentual": 10,
            }
        )
    )

    print("\nAnálise com desconto de 99%:")
    print(resultado_desconto_extremo)

    assert (
        resultado_desconto_extremo["sucesso"]
        is True
    )

    analise_extrema = (
        resultado_desconto_extremo["analise"]
    )

    assert (
        analise_extrema["vende_com_prejuizo"]
        is True
    )

    assert (
        analise_extrema["classificacao"]
        == "prejuizo"
    )

    resultado_lista = (
        analisar_descontos_todos_produtos.invoke(
            {
                "desconto_percentual": 10,
                "margem_minima_percentual": 10,
                "apenas_ativos": True,
            }
        )
    )

    print("\nAnálise de todos os produtos:")
    print(resultado_lista)

    assert resultado_lista["sucesso"] is True
    assert resultado_lista["quantidade_produtos"] > 0

    quantidade_resumo = sum(
        resultado_lista["resumo"].values()
    )

    assert (
        quantidade_resumo
        == resultado_lista["quantidade_produtos"]
    )

    print(
        "\nTodos os testes da análise de margem passaram."
    )


if __name__ == "__main__":
    testar_analise_margem()