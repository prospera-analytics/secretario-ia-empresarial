from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


ModalidadePreco = Literal[
    "pix",
    "avista",
    "preco_total",
]


@dataclass(frozen=True)
class PrecoExtraido:
    """
    Representa um único preço explicitamente publicado pela loja.
    """

    valor: Decimal
    modalidade: ModalidadePreco


def normalizar_dominio(
    dominio: str,
) -> str:
    """
    Normaliza um domínio para uso interno.
    """

    dominio_normalizado = (
        dominio.strip()
        .lower()
        .removeprefix("https://")
        .removeprefix("http://")
        .split("/")[0]
    )

    if dominio_normalizado.startswith("www."):
        dominio_normalizado = dominio_normalizado[4:]

    return dominio_normalizado


def gerar_urls_alternativas(
    url: str,
) -> list[str]:
    """
    Executa as regras específicas de URL dos concorrentes.
    """

    from web.concorrentes.magalu import (
        gerar_urls_alternativas_magalu,
    )

    return gerar_urls_alternativas_magalu(url)


def extrair_preco_concorrente(
    dominio: str,
    conteudo: str,
) -> PrecoExtraido | None:
    """
    Encaminha a extração de preço para o concorrente correto.
    """

    if not isinstance(conteudo, str):
        return None

    conteudo = conteudo.strip()

    if not conteudo:
        return None

    dominio_normalizado = normalizar_dominio(
        dominio
    )

    if dominio_normalizado == "amazon.com.br":
        from web.concorrentes.amazon import (
            extrair_preco_amazon,
        )

        return extrair_preco_amazon(
            conteudo
        )

    if dominio_normalizado == "magazineluiza.com.br":
        from web.concorrentes.magalu import (
            extrair_preco_magalu,
        )

        return extrair_preco_magalu(
            conteudo
        )

    return None


__all__ = [
    "ModalidadePreco",
    "PrecoExtraido",
    "normalizar_dominio",
    "gerar_urls_alternativas",
    "extrair_preco_concorrente",
]