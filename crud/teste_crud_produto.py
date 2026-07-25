from decimal import Decimal

from database.conexao import SessionLocal
from database.crud.produto import (
    atualizar_produto,
    buscar_produto_por_id,
    cadastrar_produto,
    desativar_produto,
    listar_produtos,
    pesquisar_produtos,
)


def testar_crud_produto() -> None:
    with SessionLocal() as sessao:
        try:
            produtos = listar_produtos(sessao)

            print("\nProdutos cadastrados:")

            for produto in produtos:
                print(
                    produto.id,
                    produto.nome,
                    produto.preco_venda,
                )

            encontrados = pesquisar_produtos(
                sessao=sessao,
                termo="Samsung",
            )

            print("\nProdutos Samsung:")

            for produto in encontrados:
                print(produto.nome)

            produto_teste = cadastrar_produto(
                sessao=sessao,
                nome="Smartphone de Teste 128 GB",
                marca="Marca Teste",
                armazenamento_gb=128,
                preco_venda=Decimal("1999.90"),
                descricao="Produto temporário para testar o CRUD.",
            )

            print("\nProduto criado:")
            print(produto_teste)

            produto_atualizado = atualizar_produto(
                sessao=sessao,
                produto_id=produto_teste.id,
                preco_venda=Decimal("1899.90"),
            )

            print("\nProduto atualizado:")
            print(produto_atualizado)

            produto_buscado = buscar_produto_por_id(
                sessao=sessao,
                produto_id=produto_teste.id,
            )

            print("\nProduto buscado:")
            print(produto_buscado)

            produto_desativado = desativar_produto(
                sessao=sessao,
                produto_id=produto_teste.id,
            )

            print("\nProduto desativado:")
            print(
                produto_desativado.nome,
                produto_desativado.ativo,
            )

            # O rollback evita deixar o produto de teste no banco.
            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_produto()