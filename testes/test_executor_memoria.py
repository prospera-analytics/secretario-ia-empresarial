from unittest.mock import patch

from agente.executor import (
    conversar_com_memoria,
)
from agente.memoria import (
    criar_memoria_vazia,
    registrar_concorrente,
    registrar_produto,
    resumir_memoria_para_modelo,
)


def test_resumo_memoria_compacto() -> None:
    memoria = criar_memoria_vazia()

    memoria = registrar_produto(
        memoria,
        {
            "id": 1,
            "nome": "Apple iPhone 16 128 GB",
            "marca": "Apple",
            "armazenamento_gb": 128,
            "preco_venda": 6499.90,
            "ativo": True,
        },
    )

    memoria = registrar_concorrente(
        memoria,
        {
            "id": 2,
            "nome": "Amazon",
            "dominio": "amazon.com.br",
            "ativo": True,
        },
    )

    resumo = resumir_memoria_para_modelo(
        memoria
    )

    assert "Apple iPhone 16 128 GB" in resumo
    assert "Amazon" in resumo
    assert len(resumo) < 1000


def test_fluxo_deterministico_nao_chama_llm() -> None:
    with patch(
        "agente.executor.executar_agente"
    ) as executar_agente_mock:
        resultado = conversar_com_memoria(
            pergunta="Liste os nossos produtos",
            memoria=criar_memoria_vazia(),
        )

    assert resultado["deterministico"] is True
    executar_agente_mock.assert_not_called()


def test_fallback_sem_ferramenta_executada_nao_inventa() -> None:
    resultado_simulado = {
        "messages": [
            type(
                "Mensagem",
                (),
                {
                    "content": (
                        "O faturamento foi R$ 1 milhão."
                    )
                },
            )()
        ],
        "_roteamento": {
            "nomes_ferramentas": [
                "consultar_vendas"
            ],
        },
        "_ferramentas_executadas": [],
    }

    with patch(
        "agente.executor.executar_agente",
        return_value=resultado_simulado,
    ):
        resultado = conversar_com_memoria(
            pergunta="Qual foi nosso faturamento?",
            memoria=criar_memoria_vazia(),
        )

    assert resultado["deterministico"] is False
    assert resultado["resposta"] == (
        "Não foi possível confirmar essa informação "
        "nos dados empresariais disponíveis."
    )