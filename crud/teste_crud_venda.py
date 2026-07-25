from datetime import date
from decimal import Decimal

from database.conexao import SessionLocal
from database.crud.estoque import (
    buscar_estoque_por_produto_id,
)
from database.crud.produto import listar_produtos
from database.crud.venda import (
    buscar_venda_por_id,
    calcular_faturamento,
    calcular_quantidade_vendida,
    calcular_valor_total,
    listar_vendas,
    produtos_mais_vendidos,
    registrar_venda,
)


def testar_crud_venda() -> None:
    with SessionLocal() as sessao:
        try:
            vendas = listar_vendas(sessao)

            print("\nVendas cadastradas:")

            for venda in vendas:
                print(
                    venda.id,
                    venda.produto.nome,
                    venda.quantidade,
                    f"R$ {calcular_valor_total(venda):,.2f}",
                    venda.data_venda,
                )

            faturamento = calcular_faturamento(sessao)

            print("\nFaturamento total:")
            print(f"R$ {faturamento:,.2f}")

            quantidade_vendida = calcular_quantidade_vendida(
                sessao
            )

            print("\nQuantidade total vendida:")
            print(quantidade_vendida)

            ranking = produtos_mais_vendidos(
                sessao=sessao,
                limite=5,
            )

            print("\nProdutos mais vendidos:")

            for produto, quantidade in ranking:
                print(
                    produto.nome,
                    quantidade,
                )

            produtos = listar_produtos(sessao)

            produto_teste = None
            estoque_original = None

            for produto in produtos:
                estoque = buscar_estoque_por_produto_id(
                    sessao=sessao,
                    produto_id=produto.id,
                )

                if (
                    estoque is not None
                    and estoque.quantidade_atual >= 1
                ):
                    produto_teste = produto
                    estoque_original = estoque.quantidade_atual
                    break

            if produto_teste is None:
                raise RuntimeError(
                    "Nenhum produto com estoque disponível."
                )

            venda_teste = registrar_venda(
                sessao=sessao,
                produto_id=produto_teste.id,
                quantidade=1,
                preco_unitario=Decimal("1999.90"),
                data_venda=date.today(),
            )

            print("\nVenda criada:")
            print(venda_teste)

            venda_buscada = buscar_venda_por_id(
                sessao=sessao,
                venda_id=venda_teste.id,
            )

            estoque_atualizado = buscar_estoque_por_produto_id(
                sessao=sessao,
                produto_id=produto_teste.id,
            )

            assert venda_buscada is not None
            assert estoque_atualizado is not None

            assert calcular_valor_total(
                venda_buscada
            ) == Decimal("1999.90")

            assert (
                estoque_atualizado.quantidade_atual
                == estoque_original - 1
            )

            print("\nEstoque após a venda:")
            print(
                produto_teste.nome,
                estoque_atualizado.quantidade_atual,
            )

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_venda()