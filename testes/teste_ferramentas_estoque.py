from agente.ferramentas.estoque import (
    adicionar_unidades_estoque,
    consultar_estoque_produto,
    consultar_estoques,
    consultar_produtos_com_estoque_baixo,
    consultar_produtos_no_estoque_minimo,
    definir_estoque_minimo_produto,
    definir_quantidade_atual_estoque,
    remover_unidades_estoque,
)


def testar_ferramentas_estoque() -> None:
    """
    Testa as ferramentas de estoque usando um produto já existente.

    As alterações feitas durante o teste são restauradas ao final.
    """

    resultado_lista = consultar_estoques.invoke(
        {
            "apenas_produtos_ativos": True,
        }
    )

    print("\nResultado da listagem:")
    print(resultado_lista)

    assert resultado_lista["sucesso"] is True
    assert "estoques" in resultado_lista
    assert resultado_lista["quantidade"] > 0

    primeiro_estoque = resultado_lista["estoques"][0]
    produto_id = primeiro_estoque["produto_id"]

    quantidade_original = primeiro_estoque["quantidade_atual"]
    minimo_original = primeiro_estoque["estoque_minimo"]

    resultado_consulta = consultar_estoque_produto.invoke(
        {
            "produto_id": produto_id,
        }
    )

    print("\nResultado da consulta por produto:")
    print(resultado_consulta)

    assert resultado_consulta["sucesso"] is True
    assert resultado_consulta["estoque"]["produto_id"] == produto_id

    try:
        resultado_adicao = adicionar_unidades_estoque.invoke(
            {
                "produto_id": produto_id,
                "quantidade": 2,
            }
        )

        print("\nResultado da adição:")
        print(resultado_adicao)

        assert resultado_adicao["sucesso"] is True
        assert (
            resultado_adicao["estoque"]["quantidade_atual"]
            == quantidade_original + 2
        )

        resultado_remocao = remover_unidades_estoque.invoke(
            {
                "produto_id": produto_id,
                "quantidade": 1,
            }
        )

        print("\nResultado da remoção:")
        print(resultado_remocao)

        assert resultado_remocao["sucesso"] is True
        assert (
            resultado_remocao["estoque"]["quantidade_atual"]
            == quantidade_original + 1
        )

        resultado_definicao = (
            definir_quantidade_atual_estoque.invoke(
                {
                    "produto_id": produto_id,
                    "nova_quantidade": 7,
                }
            )
        )

        print("\nResultado da definição da quantidade:")
        print(resultado_definicao)

        assert resultado_definicao["sucesso"] is True
        assert (
            resultado_definicao["estoque"]["quantidade_atual"]
            == 7
        )

        resultado_minimo = definir_estoque_minimo_produto.invoke(
            {
                "produto_id": produto_id,
                "novo_estoque_minimo": 8,
            }
        )

        print("\nResultado da atualização do mínimo:")
        print(resultado_minimo)

        assert resultado_minimo["sucesso"] is True
        assert resultado_minimo["estoque"]["estoque_minimo"] == 8
        assert resultado_minimo["estoque"]["abaixo_do_minimo"] is True

        resultado_baixo = (
            consultar_produtos_com_estoque_baixo.invoke({})
        )

        print("\nProdutos abaixo do mínimo:")
        print(resultado_baixo)

        assert resultado_baixo["sucesso"] is True

        ids_abaixo = {
            estoque["produto_id"]
            for estoque in resultado_baixo["estoques"]
        }

        assert produto_id in ids_abaixo

        resultado_limite = (
            definir_quantidade_atual_estoque.invoke(
                {
                    "produto_id": produto_id,
                    "nova_quantidade": 8,
                }
            )
        )

        assert resultado_limite["sucesso"] is True

        produtos_no_limite = (
            consultar_produtos_no_estoque_minimo.invoke({})
        )

        print("\nProdutos no limite:")
        print(produtos_no_limite)

        assert produtos_no_limite["sucesso"] is True

        ids_no_limite = {
            estoque["produto_id"]
            for estoque in produtos_no_limite["estoques"]
        }

        assert produto_id in ids_no_limite

    finally:
        restaurar_quantidade = (
            definir_quantidade_atual_estoque.invoke(
                {
                    "produto_id": produto_id,
                    "nova_quantidade": quantidade_original,
                }
            )
        )

        restaurar_minimo = definir_estoque_minimo_produto.invoke(
            {
                "produto_id": produto_id,
                "novo_estoque_minimo": minimo_original,
            }
        )

        print("\nRestauração da quantidade:")
        print(restaurar_quantidade)

        print("\nRestauração do estoque mínimo:")
        print(restaurar_minimo)

        assert restaurar_quantidade["sucesso"] is True
        assert restaurar_minimo["sucesso"] is True

    print("\nTodos os testes das ferramentas de estoque passaram.")


if __name__ == "__main__":
    testar_ferramentas_estoque()