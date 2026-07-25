from datetime import date, timedelta

from agente.ferramentas.compra import (
    consultar_compra_por_id,
    consultar_compras,
    consultar_compras_em_aberto,
    consultar_compras_fornecedor,
    consultar_compras_produto,
    modificar_previsao_entrega_compra,
    modificar_status_compra,
    registrar_compra,
)
from agente.ferramentas.fornecedor import (
    consultar_fornecedores,
)
from agente.ferramentas.produto import (
    consultar_produtos,
)
from database.conexao import SessionLocal
from database.models.compra import Compra


def excluir_compra_teste(
    compra_id: int,
) -> None:
    """
    Remove diretamente a compra criada pelo teste.

    Essa exclusão é apenas uma rotina de limpeza do ambiente
    de testes e não representa uma ferramenta do agente.
    """

    with SessionLocal() as sessao:
        compra = sessao.get(Compra, compra_id)

        if compra is not None:
            sessao.delete(compra)
            sessao.commit()


def testar_ferramentas_compra() -> None:
    """
    Testa registro, consultas e atualizações de uma compra.

    A compra criada durante o teste é removida ao final para não
    deixar registros artificiais no banco principal.
    """

    resultado_produtos = consultar_produtos.invoke(
        {
            "apenas_ativos": True,
        }
    )

    assert resultado_produtos["sucesso"] is True
    assert resultado_produtos["quantidade"] > 0

    resultado_fornecedores = consultar_fornecedores.invoke(
        {
            "apenas_ativos": True,
        }
    )

    assert resultado_fornecedores["sucesso"] is True
    assert resultado_fornecedores["quantidade"] > 0

    produto = resultado_produtos["produtos"][0]
    fornecedor = resultado_fornecedores["fornecedores"][0]

    produto_id = produto["id"]
    fornecedor_id = fornecedor["id"]

    hoje = date.today()
    previsao_inicial = hoje + timedelta(days=5)
    previsao_atualizada = hoje + timedelta(days=8)

    compra_id: int | None = None

    try:
        resultado_registro = registrar_compra.invoke(
            {
                "produto_id": produto_id,
                "fornecedor_id": fornecedor_id,
                "quantidade": 3,
                "preco_unitario": 1500.50,
                "data_compra": hoje.isoformat(),
                "previsao_entrega": (
                    previsao_inicial.isoformat()
                ),
                "status": "pendente",
            }
        )

        print("\nResultado do registro:")
        print(resultado_registro)

        assert resultado_registro["sucesso"] is True

        compra = resultado_registro["compra"]
        compra_id = compra["id"]

        assert compra["produto_id"] == produto_id
        assert compra["fornecedor_id"] == fornecedor_id
        assert compra["quantidade"] == 3
        assert compra["preco_unitario"] == 1500.50
        assert compra["valor_total"] == 4501.50
        assert compra["status"] == "pendente"

        resultado_consulta = consultar_compra_por_id.invoke(
            {
                "compra_id": compra_id,
            }
        )

        print("\nResultado da consulta por ID:")
        print(resultado_consulta)

        assert resultado_consulta["sucesso"] is True
        assert resultado_consulta["compra"]["id"] == compra_id

        resultado_produto = consultar_compras_produto.invoke(
            {
                "produto_id": produto_id,
            }
        )

        print("\nCompras do produto:")
        print(resultado_produto)

        assert resultado_produto["sucesso"] is True

        ids_compras_produto = {
            item["id"]
            for item in resultado_produto["compras"]
        }

        assert compra_id in ids_compras_produto

        resultado_fornecedor = (
            consultar_compras_fornecedor.invoke(
                {
                    "fornecedor_id": fornecedor_id,
                }
            )
        )

        print("\nCompras do fornecedor:")
        print(resultado_fornecedor)

        assert resultado_fornecedor["sucesso"] is True

        ids_compras_fornecedor = {
            item["id"]
            for item in resultado_fornecedor["compras"]
        }

        assert compra_id in ids_compras_fornecedor

        resultado_pendentes = (
            consultar_compras_em_aberto.invoke({})
        )

        print("\nCompras em aberto:")
        print(resultado_pendentes)

        assert resultado_pendentes["sucesso"] is True

        ids_pendentes = {
            item["id"]
            for item in resultado_pendentes["compras"]
        }

        assert compra_id in ids_pendentes

        resultado_status = modificar_status_compra.invoke(
            {
                "compra_id": compra_id,
                "novo_status": "enviado",
            }
        )

        print("\nResultado da atualização do status:")
        print(resultado_status)

        assert resultado_status["sucesso"] is True
        assert (
            resultado_status["compra"]["status"]
            == "enviado"
        )

        resultado_previsao = (
            modificar_previsao_entrega_compra.invoke(
                {
                    "compra_id": compra_id,
                    "nova_previsao": (
                        previsao_atualizada.isoformat()
                    ),
                }
            )
        )

        print("\nResultado da atualização da previsão:")
        print(resultado_previsao)

        assert resultado_previsao["sucesso"] is True
        assert (
            resultado_previsao["compra"][
                "previsao_entrega"
            ]
            == previsao_atualizada.isoformat()
        )

        resultado_lista_enviadas = consultar_compras.invoke(
            {
                "status": "enviado",
            }
        )

        print("\nCompras com status enviado:")
        print(resultado_lista_enviadas)

        assert resultado_lista_enviadas["sucesso"] is True

        ids_enviados = {
            item["id"]
            for item in resultado_lista_enviadas["compras"]
        }

        assert compra_id in ids_enviados

        resultado_cancelamento = (
            modificar_status_compra.invoke(
                {
                    "compra_id": compra_id,
                    "novo_status": "cancelado",
                }
            )
        )

        print("\nResultado do cancelamento:")
        print(resultado_cancelamento)

        assert resultado_cancelamento["sucesso"] is True
        assert (
            resultado_cancelamento["compra"]["status"]
            == "cancelado"
        )

        print(
            "\nTodos os testes das ferramentas "
            "de compra passaram."
        )

    finally:
        if compra_id is not None:
            excluir_compra_teste(compra_id)

            print(
                "\nA compra criada pelo teste foi removida "
                "do banco."
            )


if __name__ == "__main__":
    testar_ferramentas_compra()