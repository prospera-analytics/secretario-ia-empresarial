import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class ConfiguracaoAgente:
    """Configurações necessárias para executar o agente."""

    groq_api_key: str
    groq_model: str
    temperatura: float = 0.0
    max_tentativas: int = 2


def carregar_configuracao() -> ConfiguracaoAgente:
    """
    Carrega e valida as configurações do agente.

    A chave da Groq deve estar definida na variável
    de ambiente GROQ_API_KEY.
    """

    groq_api_key = os.getenv(
        "GROQ_API_KEY",
        "",
    ).strip()

    groq_model = os.getenv(
        "GROQ_MODEL",
        "qwen/qwen3-32b",
    ).strip()

    if not groq_api_key:
        raise RuntimeError(
            "A variável GROQ_API_KEY não foi definida. "
            "Crie um arquivo .env na raiz do projeto."
        )

    if not groq_model:
        raise RuntimeError(
            "A variável GROQ_MODEL não pode estar vazia."
        )

    return ConfiguracaoAgente(
        groq_api_key=groq_api_key,
        groq_model=groq_model,
    )