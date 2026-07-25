from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from agente.ferramentas.campanha import (
    associar_produto_campanha,
    consultar_campanha_por_id,
    consultar_campanha_por_nome,
    consultar_campanhas,
    consultar_campanhas_ativas,
    consultar_produtos_campanha,
    consultar_resultado_campanha,
    criar_campanha,
    modificar_campanha,
)
from database.conexao import SessionLocal
from database.models.campanha import Campanha
from database.models.produto import Produto


def localizar_produto_ativo() -> int:
    """Localiza um produto ativo para o teste."""

    with SessionLocal() as sessao:
        consulta = (
            select(Produto)
            .where(Produto.ativo.is_(True))
            .order_by(Produto.id)
            .limit(1)
        )

        produto = sessao.scalar(consulta)

        if produto is None:
            raise RuntimeError(
                "Nenhum produto ativo foi encontrado "
                "para executar o teste."
            )

        return produto.id


def excluir_campanha_teste(
    campanha_id: int,
) -> None:
    """
    Remove a campanha criada no teste.

    As associações com produtos são removidas pelo cascade
    configurado no relacionamento.
    """

    with SessionLocal() as sessao:
        try:
            campanha = sessao.get(
                Campanha,
                campanha_id,
            )

            if campanha is not None:
                sessao.delete(campanha)
                sessao.commit()

        except Exception:
            sessao.rollback()
            raise


def testar_ferramentas_campanha() -> None:
    """Testa as ferramentas de campanha."""

    produto_id = localizar_produto_ativo()

    identificador = uuid4().hex[:8]

    nome_inicial = (
        f"Campanha Teste {identificador}"
    )

    nome_atualizado = (
        f"Campanha Atualizada {identificador}"
    )

    hoje = date.today()
    data_inicio = hoje - timedelta(days=1)
    data_fim = hoje + timedelta(days=7)
    nova_data_fim = hoje + timedelta(days=10)

    campanha_id: int | None = None

    try:
        resultado_criacao = criar_campanha.invoke(
            {
                "nome": nome_inicial,
                "canal": "Instagram",
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                "investimento": 1000.00,
                "descricao": (
                    "Campanha temporária criada "
                    "pelo teste automatizado."
                ),
                "status": "ativa",
            }
        )

        print("\nResultado da criação:")
        print(resultado_criacao)

        assert resultado_criacao["sucesso"] is True

        campanha = resultado_criacao["campanha"]
        campanha_id = campanha["id"]

        assert campanha["nome"] == nome_inicial
        assert campanha["canal"] == "Instagram"
        assert campanha["status"] == "ativa"
        assert campanha["investimento"] == 1000.00
        assert (
            campanha["data_inicio"]
            == data_inicio.isoformat()
        )
        assert (
            campanha["data_fim"]
            == data_fim.isoformat()
        )

        resultado_por_id = (
            consultar_campanha_por_id.invoke(
                {
                    "campanha_id": campanha_id,
                }
            )
        )

        print("\nConsulta por ID:")
        print(resultado_por_id)

        assert resultado_por_id["sucesso"] is True
        assert (
            resultado_por_id["campanha"]["id"]
            == campanha_id
        )

        resultado_por_nome = (
            consultar_campanha_por_nome.invoke(
                {
                    "nome": nome_inicial,
                }
            )
        )

        print("\nConsulta por nome:")
        print(resultado_por_nome)

        assert resultado_por_nome["sucesso"] is True
        assert (
            resultado_por_nome["campanha"]["id"]
            == campanha_id
        )

        resultado_lista = consultar_campanhas.invoke(
            {
                "status": "ativa",
            }
        )

        print("\nCampanhas ativas por status:")
        print(resultado_lista)

        assert resultado_lista["sucesso"] is True

        ids_campanhas = {
            item["id"]
            for item in resultado_lista["campanhas"]
        }

        assert campanha_id in ids_campanhas

        resultado_ativas = (
            consultar_campanhas_ativas.invoke(
                {
                    "data_referencia": hoje.isoformat(),
                }
            )
        )

        print("\nCampanhas ativas na data atual:")
        print(resultado_ativas)

        assert resultado_ativas["sucesso"] is True

        ids_ativas = {
            item["id"]
            for item in resultado_ativas["campanhas"]
        }

        assert campanha_id in ids_ativas

        resultado_atualizacao = (
            modificar_campanha.invoke(
                {
                    "campanha_id": campanha_id,
                    "nome": nome_atualizado,
                    "canal": "Google Ads",
                    "data_fim": nova_data_fim.isoformat(),
                    "investimento": 1500.00,
                }
            )
        )

        print("\nResultado da atualização:")
        print(resultado_atualizacao)

        assert (
            resultado_atualizacao["sucesso"]
            is True
        )

        campanha_atualizada = (
            resultado_atualizacao["campanha"]
        )

        assert (
            campanha_atualizada["nome"]
            == nome_atualizado
        )
        assert (
            campanha_atualizada["canal"]
            == "Google Ads"
        )
        assert (
            campanha_atualizada["investimento"]
            == 1500.00
        )
        assert (
            campanha_atualizada["data_fim"]
            == nova_data_fim.isoformat()
        )

        resultado_associacao = (
            associar_produto_campanha.invoke(
                {
                    "campanha_id": campanha_id,
                    "produto_id": produto_id,
                    "desconto_percentual": 10.00,
                }
            )
        )

        print("\nResultado da associação:")
        print(resultado_associacao)

        assert resultado_associacao["sucesso"] is True

        associacao = resultado_associacao[
            "associacao"
        ]

        assert (
            associacao["campanha_id"]
            == campanha_id
        )
        assert associacao["produto_id"] == produto_id
        assert (
            associacao["desconto_percentual"]
            == 10.00
        )

        resultado_produtos = (
            consultar_produtos_campanha.invoke(
                {
                    "campanha_id": campanha_id,
                }
            )
        )

        print("\nProdutos da campanha:")
        print(resultado_produtos)

        assert resultado_produtos["sucesso"] is True
        assert resultado_produtos["quantidade"] == 1

        ids_produtos = {
            item["produto_id"]
            for item in resultado_produtos["produtos"]
        }

        assert produto_id in ids_produtos

        resultado_financeiro = (
            consultar_resultado_campanha.invoke(
                {
                    "campanha_id": campanha_id,
                }
            )
        )

        print("\nResultado financeiro:")
        print(resultado_financeiro)

        assert (
            resultado_financeiro["sucesso"]
            is True
        )

        assert (
            resultado_financeiro["faturamento"]
            == 0.0
        )

        assert (
            resultado_financeiro["roi_percentual"]
            == -100.0
        )

        resultado_status = modificar_campanha.invoke(
            {
                "campanha_id": campanha_id,
                "status": "finalizada",
            }
        )

        print("\nResultado da finalização:")
        print(resultado_status)

        assert resultado_status["sucesso"] is True
        assert (
            resultado_status["campanha"]["status"]
            == "finalizada"
        )

        print(
            "\nTodos os testes das ferramentas "
            "de campanha passaram."
        )

    finally:
        if campanha_id is not None:
            excluir_campanha_teste(
                campanha_id=campanha_id,
            )

            print(
                "\nA campanha criada pelo teste "
                "foi removida."
            )


if __name__ == "__main__":
    testar_ferramentas_campanha()