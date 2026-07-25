from agente.ferramentas.produto import (
    consultar_produto_por_id,
    consultar_produtos,
    pesquisar_smartphones,
)


def testar_ferramentas_produto() -> None:
    resultado_lista = consultar_produtos.invoke(
        {
            "apenas_ativos": True,
        }
    )

    print("\nResultado da listagem:")
    print(resultado_lista)

    assert resultado_lista["sucesso"] is True
    assert "produtos" in resultado_lista

    produtos = resultado_lista["produtos"]

    if produtos:
        produto_id = produtos[0]["id"]

        resultado_busca = consultar_produto_por_id.invoke(
            {
                "produto_id": produto_id,
            }
        )

        print("\nResultado da busca por ID:")
        print(resultado_busca)

        assert resultado_busca["sucesso"] is True
        assert resultado_busca["produto"]["id"] == produto_id

        termo = produtos[0]["marca"]

        resultado_pesquisa = pesquisar_smartphones.invoke(
            {
                "termo": termo,
                "apenas_ativos": True,
            }
        )

        print("\nResultado da pesquisa:")
        print(resultado_pesquisa)

        assert resultado_pesquisa["sucesso"] is True
        assert resultado_pesquisa["quantidade"] >= 1

    print("\nTeste concluído com sucesso.")


if __name__ == "__main__":
    testar_ferramentas_produto()