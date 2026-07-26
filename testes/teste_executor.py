"""
Testes básicos do executor do Secretário IA Empresarial.

Execute na raiz do projeto com:

python -m testes.teste_executor

Para executar também a chamada real ao modelo:

python -m testes.teste_executor --integracao
"""

import os
import sys
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from agente.executor import (
    criar_agente,
    extrair_resposta_final,
)
from agente.ferramentas import criar_ferramentas
from agente.prompt import PROMPT_SECRETARIO_EMPRESARIAL


load_dotenv()


def testar_prompt() -> None:
    """
    Confirma que o prompt principal foi carregado.
    """

    assert isinstance(
        PROMPT_SECRETARIO_EMPRESARIAL,
        str,
    )

    assert PROMPT_SECRETARIO_EMPRESARIAL.strip()

    assert "Secretário IA Empresarial" in (
        PROMPT_SECRETARIO_EMPRESARIAL
    )

    print("[OK] Prompt empresarial carregado.")


def testar_lista_ferramentas() -> None:
    """
    Confirma que as ferramentas foram agrupadas corretamente.
    """

    ferramentas = criar_ferramentas()

    assert ferramentas
    assert len(ferramentas) > 0

    nomes = [
        ferramenta.name
        for ferramenta in ferramentas
    ]

    assert len(nomes) == len(set(nomes)), (
        "Existem ferramentas com nomes duplicados."
    )

    nomes_esperados = {
        "analisar_desconto_produto",
        "analisar_risco_estoque_produto",
        "recomendar_fornecedor_para_reposicao",
        "consultar_alertas_produto",
        "consultar_painel_alertas_empresariais",
    }

    ausentes = nomes_esperados.difference(nomes)

    assert not ausentes, (
        "Ferramentas analíticas ausentes: "
        + ", ".join(sorted(ausentes))
    )

    print(
        f"[OK] {len(ferramentas)} ferramentas carregadas."
    )


def testar_extracao_resposta_string() -> None:
    """
    Testa uma resposta comum, cujo conteúdo é uma string.
    """

    resultado: dict[str, Any] = {
        "messages": [
            AIMessage(
                content="Teste concluído com sucesso."
            )
        ]
    }

    resposta = extrair_resposta_final(resultado)

    assert resposta == "Teste concluído com sucesso."

    print("[OK] Extração de resposta em string.")


def testar_extracao_resposta_vazia() -> None:
    """
    Confirma que um resultado sem mensagens gera erro.
    """

    try:
        extrair_resposta_final(
            {
                "messages": [],
            }
        )
    except RuntimeError:
        print("[OK] Resultado vazio tratado corretamente.")
        return

    raise AssertionError(
        "Era esperado um RuntimeError para resultado vazio."
    )


def testar_criacao_agente() -> None:
    """
    Confirma que o objeto do agente pode ser criado.

    Este teste exige GROQ_API_KEY, mas não envia uma solicitação
    para o modelo.
    """

    if not os.getenv("GROQ_API_KEY", "").strip():
        print(
            "[IGNORADO] GROQ_API_KEY não configurada."
        )
        return

    agente = criar_agente()

    assert agente is not None
    assert hasattr(agente, "invoke")

    print("[OK] Agente criado com sucesso.")


def testar_integracao_real() -> None:
    """
    Envia uma solicitação real ao modelo.

    A pergunta foi escolhida para não depender de dados específicos
    do banco e para verificar se o agente entende sua função.
    """

    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError(
            "GROQ_API_KEY não configurada."
        )

    agente = criar_agente()

    resultado = agente.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Explique em uma frase qual é a sua função "
                        "nesta empresa. Não consulte ferramentas."
                    ),
                }
            ]
        }
    )

    resposta = extrair_resposta_final(resultado)

    assert resposta

    print("[OK] Integração real com o modelo.")
    print()
    print("Resposta recebida:")
    print(resposta)


def executar_testes() -> None:
    """
    Executa os testes locais e, quando solicitado, o teste real.
    """

    testar_prompt()
    testar_lista_ferramentas()
    testar_extracao_resposta_string()
    testar_extracao_resposta_vazia()
    testar_criacao_agente()

    if "--integracao" in sys.argv:
        testar_integracao_real()

    print()
    print("Todos os testes executados com sucesso.")

def testar_execucao_com_roteamento() -> None:
    """
    Executa uma pergunta empresarial real usando roteamento seletivo.
    """

    if "--roteamento-real" not in sys.argv:
        return

    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError(
            "GROQ_API_KEY não configurada."
        )

    from agente.executor import executar_agente

    resultado = executar_agente(
        pergunta=(
            "Quais são os principais alertas e "
            "prioridades atuais da empresa?"
        )
    )

    resposta = extrair_resposta_final(
        resultado
    )

    roteamento = resultado["_roteamento"]

    assert resposta
    assert (
        roteamento["quantidade_ferramentas"]
        < 70
    )

    print()
    print("[OK] Execução com roteamento seletivo.")
    print(
        "Quantidade de ferramentas enviadas: "
        f"{roteamento['quantidade_ferramentas']}"
    )
    print(
        "Ferramentas enviadas:"
    )

    for nome in roteamento["nomes_ferramentas"]:
        print(f"- {nome}")

    print()
    print("Resposta:")
    print(resposta)


if __name__ == "__main__":
    executar_testes()