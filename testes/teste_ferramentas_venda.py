from datetime import date
from decimal import Decimal

from sqlalchemy import select

from agente.ferramentas.estoque import (
    consultar_estoque_produto,
)
from agente.ferramentas.venda import (
    consultar_faturamento,
    consultar_produtos_mais_vendidos,
    consultar_quantidade_vendida,
    consultar_venda_por_id,
    consultar_vendas,
    consultar_vendas_produto,
    registrar_nova_venda,
)
from crud.estoque import (
    definir_quantidade_estoque,
)
from database.conexao import SessionLocal
from database.models.estoque import Estoque
from database.models.produto import Produto
from database.models.venda import Venda


def localizar_produto_com_estoque() -> tuple[int, int]:
    """
    Localiza um produto ativo com pelo menos uma unidade disponível.

    Retorna o ID do produto e sua quantidade original.
    """

    with SessionLocal() as sessao:
        consulta = (
            select(Produto, Estoque)
            .join(
                Estoque,
                Estoque.produto_id == Produto.id,
            )
            .where(
                Produto.ativo.is_(True),
                Estoque.quantidade_atual > 0,
            )
            .order_by(Produto.id)
            .limit(1)
        )

        resultado = sessao.execute(
            consulta
        ).first()

        if resultado is None:
            raise RuntimeError(
                "Nenhum produto ativo com estoque disponível "
                "foi encontrado para executar o teste."
            )

        produto, estoque = resultado

        return (
            produto.id,
            estoque.quantidade_atual,
        )


def limpar_venda_teste(
    venda_id: int,
    produto_id: int,
    quantidade_original: int,
) -> None:
    """
    Exclui a venda temporária e restaura o estoque original.

    A exclusão direta é usada somente para limpeza do teste.
    """

    with SessionLocal() as sessao:
        try:
            venda = sessao.get(
                Venda,
                venda_id,
            )

            if venda is not None:
                sessao.delete(venda)
                sessao.flush()

            definir_quantidade_estoque(
                sessao=sessao,
                produto_id=produto_id,
                nova_quantidade=quantidade_original,
            )

            sessao.commit()

        except Exception:
            sessao.rollback()
            raise


def testar_ferramentas_venda() -> None:
    """
    Testa registro, redução de estoque, consultas e indicadores.

    A venda criada é removida e o estoque é restaurado ao final.
    """

    produto_id, estoque_original = (
        localizar_produto_com_estoque()
    )

    hoje = date.today()

    preco_teste = Decimal("1234.56")
    quantidade_teste = 1
    valor_total_teste = Decimal("1234.56")

    venda_id: int | None = None

    resultado_faturamento_antes = (
        consultar_faturamento.invoke(
            {
                "data_inicio": hoje.isoformat(),
                "data_fim": hoje.isoformat(),
            }
        )
    )

    assert (
        resultado_faturamento_antes["sucesso"]
        is True
    )

    faturamento_antes = Decimal(
        str(
            resultado_faturamento_antes[
                "faturamento"
            ]
        )
    )

    resultado_quantidade_antes = (
        consultar_quantidade_vendida.invoke(
            {
                "produto_id": produto_id,
                "data_inicio": hoje.isoformat(),
                "data_fim": hoje.isoformat(),
            }
        )
    )

    assert (
        resultado_quantidade_antes["sucesso"]
        is True
    )

    quantidade_antes = (
        resultado_quantidade_antes[
            "quantidade_vendida"
        ]
    )

    try:
        resultado_registro = (
            registrar_nova_venda.invoke(
                {
                    "produto_id": produto_id,
                    "quantidade": quantidade_teste,
                    "preco_unitario": float(
                        preco_teste
                    ),
                    "data_venda": hoje.isoformat(),
                    "campanha_id": None,
                }
            )
        )

        print("\nResultado do registro:")
        print(resultado_registro)

        assert resultado_registro["sucesso"] is True

        venda = resultado_registro["venda"]
        venda_id = venda["id"]

        assert venda["produto_id"] == produto_id
        assert venda["quantidade"] == quantidade_teste
        assert Decimal(
            str(venda["preco_unitario"])
        ) == preco_teste
        assert Decimal(
            str(venda["valor_total"])
        ) == valor_total_teste
        assert venda["campanha_id"] is None
        assert venda["data_venda"] == hoje.isoformat()

        resultado_estoque = (
            consultar_estoque_produto.invoke(
                {
                    "produto_id": produto_id,
                }
            )
        )

        print("\nEstoque após a venda:")
        print(resultado_estoque)

        assert resultado_estoque["sucesso"] is True

        estoque_atual = resultado_estoque[
            "estoque"
        ]["quantidade_atual"]

        assert (
            estoque_atual
            == estoque_original - quantidade_teste
        )

        resultado_consulta = (
            consultar_venda_por_id.invoke(
                {
                    "venda_id": venda_id,
                }
            )
        )

        print("\nConsulta da venda por ID:")
        print(resultado_consulta)

        assert resultado_consulta["sucesso"] is True
        assert (
            resultado_consulta["venda"]["id"]
            == venda_id
        )

        resultado_vendas_produto = (
            consultar_vendas_produto.invoke(
                {
                    "produto_id": produto_id,
                }
            )
        )

        print("\nVendas do produto:")
        print(resultado_vendas_produto)

        assert (
            resultado_vendas_produto["sucesso"]
            is True
        )

        ids_vendas_produto = {
            item["id"]
            for item in resultado_vendas_produto[
                "vendas"
            ]
        }

        assert venda_id in ids_vendas_produto

        resultado_lista = consultar_vendas.invoke(
            {
                "data_inicio": hoje.isoformat(),
                "data_fim": hoje.isoformat(),
            }
        )

        print("\nVendas realizadas hoje:")
        print(resultado_lista)

        assert resultado_lista["sucesso"] is True

        ids_vendas_periodo = {
            item["id"]
            for item in resultado_lista["vendas"]
        }

        assert venda_id in ids_vendas_periodo

        resultado_faturamento_depois = (
            consultar_faturamento.invoke(
                {
                    "data_inicio": hoje.isoformat(),
                    "data_fim": hoje.isoformat(),
                }
            )
        )

        print("\nFaturamento após a venda:")
        print(resultado_faturamento_depois)

        assert (
            resultado_faturamento_depois["sucesso"]
            is True
        )

        faturamento_depois = Decimal(
            str(
                resultado_faturamento_depois[
                    "faturamento"
                ]
            )
        )

        assert (
            faturamento_depois
            == faturamento_antes + valor_total_teste
        )

        resultado_quantidade_depois = (
            consultar_quantidade_vendida.invoke(
                {
                    "produto_id": produto_id,
                    "data_inicio": hoje.isoformat(),
                    "data_fim": hoje.isoformat(),
                }
            )
        )

        print("\nQuantidade vendida após o teste:")
        print(resultado_quantidade_depois)

        assert (
            resultado_quantidade_depois["sucesso"]
            is True
        )

        assert (
            resultado_quantidade_depois[
                "quantidade_vendida"
            ]
            == quantidade_antes + quantidade_teste
        )

        resultado_ranking = (
            consultar_produtos_mais_vendidos.invoke(
                {
                    "limite": 5,
                    "data_inicio": hoje.isoformat(),
                    "data_fim": hoje.isoformat(),
                }
            )
        )

        print("\nProdutos mais vendidos:")
        print(resultado_ranking)

        assert resultado_ranking["sucesso"] is True
        assert (
            resultado_ranking[
                "quantidade_produtos"
            ]
            >= 1
        )

        ids_ranking = {
            item["produto_id"]
            for item in resultado_ranking["produtos"]
        }

        assert produto_id in ids_ranking

        print(
            "\nTodos os testes das ferramentas "
            "de venda passaram."
        )

    finally:
        if venda_id is not None:
            limpar_venda_teste(
                venda_id=venda_id,
                produto_id=produto_id,
                quantidade_original=estoque_original,
            )

            print(
                "\nA venda de teste foi removida e o "
                "estoque original foi restaurado."
            )


if __name__ == "__main__":
    testar_ferramentas_venda()