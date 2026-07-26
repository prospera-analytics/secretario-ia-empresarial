"""
Criação e execução do Secretário IA Empresarial.
"""

from typing import Any, Sequence

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from agente.modelo import criar_modelo
from agente.prompt import PROMPT_SECRETARIO_EMPRESARIAL
from agente.roteador import (
    diagnosticar_roteamento,
    selecionar_ferramentas,
)


def criar_agente(
    ferramentas: Sequence[BaseTool] | None = None,
):
    """
    Cria uma instância do Secretário IA Empresarial.

    O agente recebe apenas as ferramentas fornecidas.

    Quando nenhuma lista é fornecida, cria um agente sem ferramentas.
    A seleção automática acontece em executar_agente(), com base na
    pergunta do usuário.
    """

    modelo = criar_modelo()

    ferramentas_agente = list(
        ferramentas or []
    )

    return create_agent(
        model=modelo,
        tools=ferramentas_agente,
        system_prompt=PROMPT_SECRETARIO_EMPRESARIAL,
    )


def _extrair_texto_conteudo(
    conteudo: Any,
) -> str:
    """
    Converte o conteúdo retornado pelo modelo em texto.

    O conteúdo pode ser uma string ou uma lista de blocos.
    """

    if isinstance(conteudo, str):
        return conteudo

    if isinstance(conteudo, list):
        partes: list[str] = []

        for bloco in conteudo:
            if isinstance(bloco, str):
                partes.append(
                    bloco
                )
                continue

            if isinstance(bloco, dict):
                texto = bloco.get(
                    "text"
                )

                if texto:
                    partes.append(
                        str(texto)
                    )

        if partes:
            return "\n".join(
                partes
            )

    if conteudo is None:
        return ""

    return str(
        conteudo
    )


def extrair_resposta_final(
    resultado: dict[str, Any],
) -> str:
    """
    Extrai o texto da última mensagem retornada pelo agente.
    """

    mensagens = resultado.get(
        "messages",
        [],
    )

    if not mensagens:
        raise RuntimeError(
            "O agente não retornou nenhuma mensagem."
        )

    ultima_mensagem = mensagens[-1]

    conteudo = getattr(
        ultima_mensagem,
        "content",
        ultima_mensagem,
    )

    resposta = _extrair_texto_conteudo(
        conteudo
    ).strip()

    if not resposta:
        raise RuntimeError(
            "O agente retornou uma resposta vazia."
        )

    return resposta


def executar_agente(
    pergunta: str,
    historico: Sequence[BaseMessage] | None = None,
    ferramentas: Sequence[BaseTool] | None = None,
) -> dict[str, Any]:
    """
    Executa o Secretário IA Empresarial.

    Quando ferramentas não são informadas explicitamente, o roteador
    seleciona automaticamente apenas as ferramentas necessárias.

    Uma lista vazia pode ser fornecida explicitamente para executar
    o modelo sem ferramentas.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    if ferramentas is None:
        ferramentas_selecionadas = (
            selecionar_ferramentas(
                pergunta_limpa
            )
        )
    else:
        ferramentas_selecionadas = list(
            ferramentas
        )

    mensagens: list[Any] = list(
        historico or []
    )

    mensagens.append(
        {
            "role": "user",
            "content": pergunta_limpa,
        }
    )

    agente = criar_agente(
        ferramentas=(
            ferramentas_selecionadas
        ),
    )

    resultado = agente.invoke(
        {
            "messages": mensagens,
        }
    )

    resultado["_roteamento"] = {
        "quantidade_ferramentas": len(
            ferramentas_selecionadas
        ),
        "nomes_ferramentas": [
            ferramenta.name
            for ferramenta
            in ferramentas_selecionadas
        ],
    }

    return resultado


def conversar(
    pergunta: str,
    historico: Sequence[BaseMessage] | None = None,
    ferramentas: Sequence[BaseTool] | None = None,
) -> str:
    """
    Envia uma pergunta ao agente e retorna somente a resposta final.
    """

    resultado = executar_agente(
        pergunta=pergunta,
        historico=historico,
        ferramentas=ferramentas,
    )

    return extrair_resposta_final(
        resultado
    )


def visualizar_roteamento(
    pergunta: str,
) -> dict[str, object]:
    """
    Mostra como uma pergunta será roteada sem chamar a Groq.
    """

    return diagnosticar_roteamento(
        pergunta
    )


__all__ = [
    "conversar",
    "criar_agente",
    "executar_agente",
    "extrair_resposta_final",
    "visualizar_roteamento",
]