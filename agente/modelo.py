from langchain_groq import ChatGroq

from agente.configuracao import (
    ConfiguracaoAgente,
    carregar_configuracao,
)


def criar_modelo(
    configuracao: ConfiguracaoAgente | None = None,
) -> ChatGroq:
    """
    Cria o modelo de linguagem usado pelo secretário empresarial.
    """

    config = configuracao or carregar_configuracao()

    return ChatGroq(
        api_key=config.groq_api_key,
        model=config.groq_model,
        temperature=config.temperatura,
        max_retries=config.max_tentativas,
        timeout=60,
    )