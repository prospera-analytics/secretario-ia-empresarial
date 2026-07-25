from database.conexao import SessionLocal
from database.crud.estoque import (
    adicionar_ao_estoque,
    atualizar_estoque_minimo,
    buscar_estoque_por_produto_id,
    listar_estoques,
    listar_produtos_abaixo_do_minimo,
    listar_produtos_no_limite,
    remover_do_estoque,
)


def testar_crud_estoque() -> None:
    with SessionLocal() as sessao:
        try:
            estoques = listar_estoques(sessao)

            print("\nEstoques cadastrados:")

            for estoque in estoques:
                print(
                    estoque.produto.nome,
                    f"atual={estoque.quantidade_atual}",
                    f"mínimo={estoque.estoque_minimo}",
                )

            abaixo_do_minimo = listar_produtos_abaixo_do_minimo(
                sessao
            )

            print("\nProdutos abaixo do estoque mínimo:")

            for estoque in abaixo_do_minimo:
                print(
                    estoque.produto.nome,
                    estoque.quantidade_atual,
                    estoque.estoque_minimo,
                )

            no_limite = listar_produtos_no_limite(sessao)

            print("\nProdutos no limite mínimo:")

            for estoque in no_limite:
                print(
                    estoque.produto.nome,
                    estoque.quantidade_atual,
                )

            if not estoques:
                raise RuntimeError(
                    "Nenhum estoque foi encontrado para o teste."
                )

            produto_id = estoques[0].produto_id
            quantidade_original = estoques[0].quantidade_atual
            minimo_original = estoques[0].estoque_minimo

            estoque_adicionado = adicionar_ao_estoque(
                sessao=sessao,
                produto_id=produto_id,
                quantidade=5,
            )

            print("\nApós adicionar 5 unidades:")
            print(
                estoque_adicionado.produto.nome,
                estoque_adicionado.quantidade_atual,
            )

            estoque_removido = remover_do_estoque(
                sessao=sessao,
                produto_id=produto_id,
                quantidade=2,
            )

            print("\nApós remover 2 unidades:")
            print(
                estoque_removido.produto.nome,
                estoque_removido.quantidade_atual,
            )

            estoque_atualizado = atualizar_estoque_minimo(
                sessao=sessao,
                produto_id=produto_id,
                novo_estoque_minimo=minimo_original + 1,
            )

            print("\nNovo estoque mínimo:")
            print(
                estoque_atualizado.produto.nome,
                estoque_atualizado.estoque_minimo,
            )

            estoque_buscado = buscar_estoque_por_produto_id(
                sessao=sessao,
                produto_id=produto_id,
            )

            print("\nEstoque buscado:")
            print(estoque_buscado)

            assert estoque_buscado is not None
            assert (
                estoque_buscado.quantidade_atual
                == quantidade_original + 3
            )
            assert (
                estoque_buscado.estoque_minimo
                == minimo_original + 1
            )

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_estoque()