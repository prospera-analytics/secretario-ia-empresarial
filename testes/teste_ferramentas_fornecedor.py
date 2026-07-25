from uuid import uuid4

from agente.ferramentas.fornecedor import (
    consultar_fornecedor_por_id,
    consultar_fornecedores,
    criar_fornecedor,
    desativar_fornecedor_cadastrado,
    modificar_fornecedor,
    pesquisar_fornecedores_cadastrados,
    reativar_fornecedor_cadastrado,
)


def testar_ferramentas_fornecedor() -> None:
    """
    Testa consulta, criação, atualização, desativação e reativação.

    Um nome aleatório é usado para evitar conflito com fornecedores
    já cadastrados no banco.
    """

    resultado_lista = consultar_fornecedores.invoke(
        {
            "apenas_ativos": True,
        }
    )

    print("\nResultado da listagem:")
    print(resultado_lista)

    assert resultado_lista["sucesso"] is True
    assert "fornecedores" in resultado_lista

    sufixo = uuid4().hex[:8]
    nome_fornecedor = f"Fornecedor Teste {sufixo}"

    resultado_criacao = criar_fornecedor.invoke(
        {
            "nome": nome_fornecedor,
            "cidade": "São José dos Campos",
            "estado": "SP",
            "prazo_entrega_dias": 5,
        }
    )

    print("\nResultado da criação:")
    print(resultado_criacao)

    assert resultado_criacao["sucesso"] is True

    fornecedor_id = resultado_criacao["fornecedor"]["id"]

    resultado_consulta = consultar_fornecedor_por_id.invoke(
        {
            "fornecedor_id": fornecedor_id,
        }
    )

    print("\nResultado da consulta por ID:")
    print(resultado_consulta)

    assert resultado_consulta["sucesso"] is True
    assert (
        resultado_consulta["fornecedor"]["nome"]
        == nome_fornecedor
    )

    resultado_pesquisa = (
        pesquisar_fornecedores_cadastrados.invoke(
            {
                "termo": sufixo,
                "apenas_ativos": True,
            }
        )
    )

    print("\nResultado da pesquisa:")
    print(resultado_pesquisa)

    assert resultado_pesquisa["sucesso"] is True
    assert resultado_pesquisa["quantidade"] >= 1

    ids_encontrados = {
        fornecedor["id"]
        for fornecedor in resultado_pesquisa["fornecedores"]
    }

    assert fornecedor_id in ids_encontrados

    resultado_atualizacao = modificar_fornecedor.invoke(
        {
            "fornecedor_id": fornecedor_id,
            "cidade": "Campinas",
            "estado": "sp",
            "prazo_entrega_dias": 7,
        }
    )

    print("\nResultado da atualização:")
    print(resultado_atualizacao)

    assert resultado_atualizacao["sucesso"] is True
    assert (
        resultado_atualizacao["fornecedor"]["cidade"]
        == "Campinas"
    )
    assert (
        resultado_atualizacao["fornecedor"]["estado"]
        == "SP"
    )
    assert (
        resultado_atualizacao["fornecedor"][
            "prazo_entrega_dias"
        ]
        == 7
    )

    resultado_desativacao = (
        desativar_fornecedor_cadastrado.invoke(
            {
                "fornecedor_id": fornecedor_id,
            }
        )
    )

    print("\nResultado da desativação:")
    print(resultado_desativacao)

    assert resultado_desativacao["sucesso"] is True
    assert (
        resultado_desativacao["fornecedor"]["ativo"]
        is False
    )

    resultado_pesquisa_ativos = (
        pesquisar_fornecedores_cadastrados.invoke(
            {
                "termo": sufixo,
                "apenas_ativos": True,
            }
        )
    )

    assert resultado_pesquisa_ativos["sucesso"] is True

    ids_ativos = {
        fornecedor["id"]
        for fornecedor in resultado_pesquisa_ativos[
            "fornecedores"
        ]
    }

    assert fornecedor_id not in ids_ativos

    resultado_reativacao = (
        reativar_fornecedor_cadastrado.invoke(
            {
                "fornecedor_id": fornecedor_id,
            }
        )
    )

    print("\nResultado da reativação:")
    print(resultado_reativacao)

    assert resultado_reativacao["sucesso"] is True
    assert (
        resultado_reativacao["fornecedor"]["ativo"]
        is True
    )

    print(
        "\nTodos os testes das ferramentas "
        "de fornecedor passaram."
    )


if __name__ == "__main__":
    testar_ferramentas_fornecedor()