from __future__ import annotations

import streamlit as st

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
)

from agente.executor import (
    conversar_com_memoria,
)

from agente.memoria import (
    criar_memoria_vazia,
    normalizar_memoria,
)

from database.criar_banco import criar_banco
from database.popular_banco import popular_banco

LIMITE_PERGUNTAS_HISTORICO = 2


def _inicializar_estado() -> None:
    """
    Inicializa o histórico visual e a memória factual.
    """

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    if "memoria" not in st.session_state:
        st.session_state.memoria = (
            criar_memoria_vazia()
        )
    else:
        st.session_state.memoria = (
            normalizar_memoria(
                st.session_state.memoria
            )
        )


def _converter_historico_para_langchain() -> list[BaseMessage]:
    """
    Converte somente perguntas recentes do usuário.

    A memória factual é armazenada separadamente e não depende
    das respostas anteriores produzidas pelo modelo.
    """

    mensagens_usuario = [
        mensagem
        for mensagem in st.session_state.mensagens
        if mensagem["role"] == "user"
    ]

    mensagens_recentes = mensagens_usuario[
        -LIMITE_PERGUNTAS_HISTORICO:
    ]

    return [
        HumanMessage(
            content=mensagem["content"],
        )
        for mensagem in mensagens_recentes
    ]


def _mostrar_historico() -> None:
    """
    Exibe todas as mensagens da conversa atual.
    """

    for mensagem in st.session_state.mensagens:
        with st.chat_message(
            mensagem["role"]
        ):
            st.markdown(
                mensagem["content"]
            )


def _limpar_conversa() -> None:
    """
    Remove histórico visual e memória factual.
    """

    st.session_state.mensagens = []
    st.session_state.memoria = (
        criar_memoria_vazia()
    )


def _registrar_mensagem(
    role: str,
    content: str,
) -> None:
    """
    Salva uma mensagem no histórico visual.
    """

    st.session_state.mensagens.append(
        {
            "role": role,
            "content": content,
        }
    )


def _formatar_erro(
    erro: Exception,
) -> str:
    """
    Converte exceções em mensagens adequadas para a interface.
    """

    mensagem = str(
        erro
    ).strip()

    if (
        "Request too large" in mensagem
        or "tokens per minute" in mensagem
        or "rate_limit_exceeded" in mensagem
    ):
        return (
            "O limite diário de uso do modelo de IA foi atingido. Aguarde alguns minutos até a renovação da cota ou utilize uma chave de API com um plano de maior capacidade.\n\n"
            f"Detalhes técnicos: `{mensagem}`"
        )

    if (
        "Nenhuma ferramenta de preço concorrente"
        in mensagem
    ):
        return (
            "A consulta de preço concorrente não pôde ser "
            "roteada corretamente."
        )

    return (
        "Não foi possível concluir a consulta.\n\n"
        f"Detalhes técnicos: `{mensagem}`"
    )

@st.cache_resource
def _inicializar_banco() -> None:
    """
    Cria as tabelas e popula o banco apenas quando necessário.
    """

    criar_banco()
    popular_banco(limpar=False)

def main() -> None:
    st.set_page_config(
        page_title="Secretário IA Empresarial",
        page_icon="🤖",
        layout="centered",
    )

    _inicializar_banco()
    _inicializar_estado()

    st.title(
        "🤖 Secretário IA Empresarial"
    )

    st.write(
        "Faça uma pergunta sobre produtos, estoque, vendas, "
        "fornecedores, campanhas, concorrentes ou análises "
        "da empresa."
    )

    st.markdown(
        "### 💡 Perguntas de exemplo"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📦 Produto com maior risco de ruptura",
            use_container_width=True,
        ):
            st.session_state.pergunta_exemplo = (
                "Qual produto apresenta maior risco de ruptura "
                "e por quê?"
            )

        if st.button(
            "🚚 Melhor fornecedor",
            use_container_width=True,
        ):
            st.session_state.pergunta_exemplo = (
                "Quem oferece a melhor combinação de custo "
                "e prazo para o Samsung Galaxy S25 Ultra "
                "512 GB?"
            )

    with col2:
        if st.button(
            "📉 Vale a pena reduzir o preço?",
            use_container_width=True,
        ):
            st.session_state.pergunta_exemplo = (
                "Vale a pena reduzir nosso preço do "
                "iPhone 16 128 GB?"
            )

        if st.button(
            "📊 Comparar catálogo",
            use_container_width=True,
        ):
            st.session_state.pergunta_exemplo = (
                "Compare todos os nossos produtos com produtos "
                "equivalentes ou iguais de concorrentes."
            )

    with st.sidebar:
        st.header(
            "Conversa"
        )

        st.button(
            "Limpar conversa",
            on_click=_limpar_conversa,
            use_container_width=True,
        )

        st.caption(
            "O histórico visual e o contexto factual "
            "são mantidos separadamente."
        )

    _mostrar_historico()

    pergunta = st.chat_input(
        "Digite sua pergunta..."
    )

    if not pergunta:
        pergunta = st.session_state.pop(
            "pergunta_exemplo",
            None,
        )

    if not pergunta:
        return

    pergunta = pergunta.strip()

    if not pergunta:
        return

    historico_anterior = (
        _converter_historico_para_langchain()
    )

    _registrar_mensagem(
        role="user",
        content=pergunta,
    )

    with st.chat_message(
        "user"
    ):
        st.markdown(
            pergunta
        )

    with st.chat_message(
        "assistant"
    ):
        with st.spinner(
            "Analisando os dados da empresa..."
        ):
            try:
                resultado = conversar_com_memoria(
                    pergunta=pergunta,
                    memoria=st.session_state.memoria,
                    historico=historico_anterior,
                )

                resposta = resultado["resposta"]

                st.session_state.memoria = (
                    resultado["memoria"]
                )

            except Exception as erro:
                resposta = _formatar_erro(
                    erro
                )

        st.markdown(
            resposta
        )

    _registrar_mensagem(
        role="assistant",
        content=resposta,
    )


if __name__ == "__main__":
    main()