from uuid import uuid4

from sqlalchemy import delete, select

from agente.ferramentas.concorrente import (
    criar_concorrente,
)
from agente.ferramentas.preco_concorrente import (
    consultar_menor_preco_concorrente,
    consultar_oferta_concorrente_por_id,
    consultar_ofertas_concorrentes,
    consultar_ofertas_por_produto,
    marcar_oferta_disponivel,
    marcar_oferta_indisponivel,
    registrar_oferta_concorrente,
)
from database.conexao import SessionLocal
from database.models.concorrente import Concorrente
from database.models.preco_concorrente import (
    PrecoConcorrente,
)
from database.models.produto import Produto


def localizar_produto_ativo() -> Produto:
    """Localiza um produto ativo para o teste."""

    with SessionLocal() as sessao:
        consulta = (
            select(Produto)
            .where(Produto.ativo.is_(True))
            .order_by(Produto.id.asc())
            .limit(1)
        )

        produto = sessao.scalar(consulta)

        if produto is None:
            raise RuntimeError(
                "Nenhum produto ativo foi encontrado "
                "para executar o teste."
            )

        sessao.expunge(produto)

        return produto


def limpar_dados_teste(
    concorrente_id: int,
) -> None:
    """Remove ofertas e concorrente criados pelo teste."""

    with SessionLocal() as sessao:
        try:
            sessao.execute(
                delete(PrecoConcorrente).where(
                    PrecoConcorrente.concorrente_id
                    == concorrente_id
                )
            )

            concorrente = sessao.get(
                Concorrente,
                concorrente_id,
            )

            if concorrente is not None:
                sessao.delete(concorrente)

            sessao.commit()

        except Exception:
            sessao.rollback()
            raise


def testar_ferramentas_preco_concorrente() -> None:
    """Testa as ferramentas de ofertas concorrentes."""

    produto = localizar_produto_ativo()

    identificador = uuid4().hex[:8]

    dominio = (
        f"precos-{identificador}.com.br"
    )

    concorrente_id: int | None = None
    oferta_1_id: int | None = None
    oferta_2_id: int | None = None

    try:
        resultado_concorrente = criar_concorrente.invoke(
            {
                "nome": (
                    f"Loja de Preços {identificador}"
                ),
                "dominio": dominio,
                "ativo": True,
            }
        )

        print("\nCriação do concorrente:")
        print(resultado_concorrente)

        assert resultado_concorrente["sucesso"] is True

        concorrente_id = resultado_concorrente[
            "concorrente"
        ]["id"]

        resultado_oferta_1 = (
            registrar_oferta_concorrente.invoke(
                {
                    "produto_id": produto.id,
                    "concorrente_id": concorrente_id,
                    "nome_produto_encontrado": (
                        f"{produto.nome} Oferta Exata"
                    ),
                    "preco": 2500.00,
                    "url": (
                        f"https://{dominio}/produto-exato"
                    ),
                    "similaridade": 0.98,
                    "tipo_correspondencia": "exato",
                    "moeda": "BRL",
                    "disponivel": True,
                }
            )
        )

        print("\nPrimeira oferta:")
        print(resultado_oferta_1)

        assert resultado_oferta_1["sucesso"] is True

        oferta_1 = resultado_oferta_1["oferta"]
        oferta_1_id = oferta_1["id"]

        assert oferta_1["produto_id"] == produto.id
        assert (
            oferta_1["concorrente_id"]
            == concorrente_id
        )
        assert oferta_1["preco"] == 2500.00
        assert oferta_1["similaridade"] == 0.98
        assert (
            oferta_1["tipo_correspondencia"]
            == "exato"
        )
        assert oferta_1["disponivel"] is True

        resultado_oferta_2 = (
            registrar_oferta_concorrente.invoke(
                {
                    "produto_id": produto.id,
                    "concorrente_id": concorrente_id,
                    "nome_produto_encontrado": (
                        f"{produto.nome} Produto Similar"
                    ),
                    "preco": 2300.00,
                    "url": (
                        f"https://{dominio}/produto-similar"
                    ),
                    "similaridade": 0.85,
                    "tipo_correspondencia": "similar",
                    "moeda": "BRL",
                    "disponivel": True,
                }
            )
        )

        print("\nSegunda oferta:")
        print(resultado_oferta_2)

        assert resultado_oferta_2["sucesso"] is True

        oferta_2 = resultado_oferta_2["oferta"]
        oferta_2_id = oferta_2["id"]

        assert oferta_2["preco"] == 2300.00
        assert (
            oferta_2["tipo_correspondencia"]
            == "similar"
        )

        resultado_por_id = (
            consultar_oferta_concorrente_por_id.invoke(
                {
                    "preco_concorrente_id": (
                        oferta_1_id
                    ),
                }
            )
        )

        print("\nConsulta da oferta por ID:")
        print(resultado_por_id)

        assert resultado_por_id["sucesso"] is True
        assert (
            resultado_por_id["oferta"]["id"]
            == oferta_1_id
        )

        resultado_lista = (
            consultar_ofertas_concorrentes.invoke(
                {
                    "produto_id": produto.id,
                    "concorrente_id": concorrente_id,
                    "apenas_disponiveis": True,
                }
            )
        )

        print("\nLista de ofertas:")
        print(resultado_lista)

        assert resultado_lista["sucesso"] is True
        assert resultado_lista["quantidade"] == 2

        resultado_por_produto = (
            consultar_ofertas_por_produto.invoke(
                {
                    "produto_id": produto.id,
                    "apenas_disponiveis": True,
                }
            )
        )

        print("\nOfertas por produto:")
        print(resultado_por_produto)

        assert resultado_por_produto["sucesso"] is True

        ofertas_teste = [
            item
            for item in resultado_por_produto["ofertas"]
            if item["concorrente_id"] == concorrente_id
        ]

        assert len(ofertas_teste) == 2
        assert ofertas_teste[0]["preco"] == 2300.00
        assert ofertas_teste[1]["preco"] == 2500.00

        resultado_menor_geral = (
            consultar_menor_preco_concorrente.invoke(
                {
                    "produto_id": produto.id,
                    "apenas_correspondencia_exata": False,
                }
            )
        )

        print("\nMenor preço geral:")
        print(resultado_menor_geral)

        assert resultado_menor_geral["sucesso"] is True
        assert resultado_menor_geral["encontrado"] is True

        resultado_menor_exato = (
            consultar_menor_preco_concorrente.invoke(
                {
                    "produto_id": produto.id,
                    "apenas_correspondencia_exata": True,
                }
            )
        )

        print("\nMenor preço com correspondência exata:")
        print(resultado_menor_exato)

        assert resultado_menor_exato["sucesso"] is True
        assert resultado_menor_exato["encontrado"] is True
        assert (
            resultado_menor_exato["oferta"][
                "tipo_correspondencia"
            ]
            == "exato"
        )

        resultado_indisponivel = (
            marcar_oferta_indisponivel.invoke(
                {
                    "preco_concorrente_id": (
                        oferta_2_id
                    ),
                }
            )
        )

        print("\nOferta marcada como indisponível:")
        print(resultado_indisponivel)

        assert resultado_indisponivel["sucesso"] is True
        assert (
            resultado_indisponivel["oferta"][
                "disponivel"
            ]
            is False
        )

        resultado_disponiveis = (
            consultar_ofertas_concorrentes.invoke(
                {
                    "produto_id": produto.id,
                    "concorrente_id": concorrente_id,
                    "apenas_disponiveis": True,
                }
            )
        )

        assert resultado_disponiveis["quantidade"] == 1

        resultado_reativacao = (
            marcar_oferta_disponivel.invoke(
                {
                    "preco_concorrente_id": (
                        oferta_2_id
                    ),
                }
            )
        )

        print("\nOferta marcada novamente como disponível:")
        print(resultado_reativacao)

        assert resultado_reativacao["sucesso"] is True
        assert (
            resultado_reativacao["oferta"]["disponivel"]
            is True
        )

        print(
            "\nTodos os testes das ferramentas de "
            "preço concorrente passaram."
        )

    finally:
        if concorrente_id is not None:
            limpar_dados_teste(
                concorrente_id=concorrente_id,
            )

            print(
                "\nAs ofertas e o concorrente criados "
                "pelo teste foram removidos."
            )


if __name__ == "__main__":
    testar_ferramentas_preco_concorrente()