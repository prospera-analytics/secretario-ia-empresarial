from sqlalchemy import select

from agente.ferramentas.analises import (
    consultar_alertas_produto,
    consultar_painel_alertas_empresariais,
)
from database.conexao import SessionLocal
from database.models.produto import Produto


SEVERIDADES_VALIDAS = {
    "critico",
    "atencao",
    "informativo",
}


TIPOS_ESPERADOS = {
    "estoque",
    "compra_atrasada",
    "margem",
    "custo_desconhecido",
    "concorrencia",
    "fornecedor",
}


def localizar_produto_ativo() -> int:
    """Localiza o primeiro produto ativo do banco."""

    with SessionLocal() as sessao:
        consulta = (
            select(Produto.id)
            .where(
                Produto.ativo.is_(True)
            )
            .order_by(
                Produto.id.asc()
            )
            .limit(1)
        )

        produto_id = sessao.scalar(
            consulta
        )

        if produto_id is None:
            raise RuntimeError(
                "Nenhum produto ativo foi encontrado."
            )

        return produto_id


def testar_alertas() -> None:
    """Testa os alertas de produto e o painel empresarial."""

    produto_id = localizar_produto_ativo()

    resultado_produto = (
        consultar_alertas_produto.invoke(
            {
                "produto_id": produto_id,
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
                "margem_minima_percentual": 10,
                "diferenca_concorrente_alerta_percentual": 3,
                "incluir_informativos": True,
            }
        )
    )

    print("\nAlertas do produto:")
    print(resultado_produto)

    assert resultado_produto["sucesso"] is True
    assert resultado_produto["produto_id"] == produto_id

    assert (
        resultado_produto["quantidade_alertas"]
        == len(resultado_produto["alertas"])
    )

    total_resumo_produto = sum(
        resultado_produto["resumo"].values()
    )

    assert (
        total_resumo_produto
        == resultado_produto["quantidade_alertas"]
    )

    for alerta in resultado_produto["alertas"]:
        assert alerta["produto_id"] == produto_id

        assert (
            alerta["severidade"]
            in SEVERIDADES_VALIDAS
        )

        assert alerta["tipo"] in TIPOS_ESPERADOS
        assert alerta["titulo"]
        assert alerta["mensagem"]
        assert alerta["recomendacao"]

    resultado_painel = (
        consultar_painel_alertas_empresariais.invoke(
            {
                "dias_analise": 30,
                "dias_cobertura_desejada": 30,
                "margem_minima_percentual": 10,
                "diferenca_concorrente_alerta_percentual": 3,
                "apenas_ativos": True,
                "incluir_informativos": True,
            }
        )
    )

    print("\nPainel de alertas empresariais:")
    print(resultado_painel)

    assert resultado_painel["sucesso"] is True

    assert (
        resultado_painel[
            "quantidade_produtos_analisados"
        ]
        > 0
    )

    assert (
        resultado_painel["quantidade_alertas"]
        == len(resultado_painel["alertas"])
    )

    total_resumo_painel = sum(
        resultado_painel["resumo"].values()
    )

    assert (
        total_resumo_painel
        == resultado_painel["quantidade_alertas"]
    )

    assert (
        resultado_painel[
            "quantidade_produtos_com_alerta"
        ]
        <= resultado_painel[
            "quantidade_produtos_analisados"
        ]
    )

    for alerta in resultado_painel["alertas"]:
        assert (
            alerta["severidade"]
            in SEVERIDADES_VALIDAS
        )

        assert alerta["tipo"] in TIPOS_ESPERADOS

    ordem = {
        "critico": 0,
        "atencao": 1,
        "informativo": 2,
    }

    valores_ordem = [
        ordem[alerta["severidade"]]
        for alerta in resultado_painel["alertas"]
    ]

    assert valores_ordem == sorted(
        valores_ordem
    )

    print(
        "\nTodos os testes dos alertas passaram."
    )


if __name__ == "__main__":
    testar_alertas()