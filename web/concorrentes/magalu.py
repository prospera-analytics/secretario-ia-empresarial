from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from web.concorrentes import PrecoExtraido


DOMINIO_MAGALU = "magazineluiza.com.br"


_VALOR_BRL = (
    r"(?P<valor>"
    r"\d{1,3}"
    r"(?:\.\d{3})*"
    r",\d{2}"
    r")"
)


_PADRAO_PRECO_PIX_MAGALU = re.compile(
    rf"""
    R\$\s*
    {_VALOR_BRL}

    \s*
    (?:
        no\s+pix\b
        |
        (?:à|a)\s+vista\b
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


_PADRAO_PRECO_TOTAL_PARCELADO_MAGALU = re.compile(
    rf"""
    (?:ou\s*)?

    R\$\s*
    {_VALOR_BRL}

    \s*
    em\s+
    (?:at[eé]\s+)?
    \d{{1,2}}\s*x\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


_PADRAO_PRECO_TOTAL_PARCELAS_SEM_EM_MAGALU = re.compile(
    rf"""
    (?:ou\s*)?

    R\$\s*
    {_VALOR_BRL}

    \s*
    \d{{1,2}}\s*x\s+de\s+R\$
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


def _converter_valor_brl(
    valor: str,
) -> Decimal | None:
    """
    Converte um valor monetário brasileiro para Decimal.

    Exemplo:

    5.099,00 -> Decimal("5099.00")
    """

    try:
        preco = Decimal(
            valor
            .replace(".", "")
            .replace(",", ".")
        )
    except InvalidOperation:
        return None

    if preco <= 0:
        return None

    return preco


def _criar_preco_extraido(
    resultado: re.Match[str] | None,
    modalidade: str,
) -> PrecoExtraido | None:
    """
    Converte uma correspondência de expressão regular em
    um preço extraído.
    """

    if resultado is None:
        return None

    valor = _converter_valor_brl(
        resultado.group("valor")
    )

    if valor is None:
        return None

    return PrecoExtraido(
        valor=valor,
        modalidade=modalidade,
    )


def extrair_preco_magalu(
    conteudo: str,
) -> PrecoExtraido | None:
    """
    Extrai no máximo um preço explícito do Magazine Luiza.

    Prioridade:

    1. preço explicitamente associado ao Pix ou à vista;
    2. preço total seguido por uma condição de parcelamento;
    3. preço total seguido imediatamente por "Nx de R$".

    Exemplos reconhecidos:

    - R$ 5.999,00 no Pix
    - R$ 5.999,00 à vista
    - R$ 6.499,00 em até 10x
    - R$ 6.499,00 em 10x de R$ 649,90
    - R$ 6.499,00 10x de R$ 649,90

    A função não:

    - calcula descontos;
    - soma parcelas;
    - interpreta o valor de uma parcela como preço total.
    """

    if not isinstance(
        conteudo,
        str,
    ):
        return None

    conteudo = conteudo.strip()

    if not conteudo:
        return None

    resultado_pix = (
        _PADRAO_PRECO_PIX_MAGALU.search(
            conteudo
        )
    )

    preco_pix = _criar_preco_extraido(
        resultado=resultado_pix,
        modalidade="avista",
    )

    if preco_pix is not None:
        return preco_pix

    resultado_total_parcelado = (
        _PADRAO_PRECO_TOTAL_PARCELADO_MAGALU.search(
            conteudo
        )
    )

    preco_total = _criar_preco_extraido(
        resultado=resultado_total_parcelado,
        modalidade="preco_total",
    )

    if preco_total is not None:
        return preco_total

    resultado_total_sem_em = (
        _PADRAO_PRECO_TOTAL_PARCELAS_SEM_EM_MAGALU.search(
            conteudo
        )
    )

    return _criar_preco_extraido(
        resultado=resultado_total_sem_em,
        modalidade="preco_total",
    )


def gerar_url_divulgador_magalu(
    url: str,
) -> str | None:
    """
    Converte uma URL oficial do Magazine Luiza em uma URL oficial
    de divulgador.

    Remove prefixos de parceiros, como:

    - /livelo/
    - /parceiros/
    - outros prefixos existentes antes do slug do produto
    """

    if not isinstance(
        url,
        str,
    ):
        return None

    url = url.strip()

    if not url:
        return None

    try:
        partes = urlsplit(
            url
        )
    except ValueError:
        return None

    dominio = partes.netloc.lower()

    if dominio.startswith(
        "www."
    ):
        dominio = dominio[4:]

    if not (
        dominio == DOMINIO_MAGALU
        or dominio.endswith(
            f".{DOMINIO_MAGALU}"
        )
    ):
        return None

    caminho = re.sub(
        r"/+",
        "/",
        partes.path,
    )

    padrao = re.compile(
        r"^"
        r"(?:/[^/]+)*"
        r"/(?P<slug>[^/]+)"
        r"/p/"
        r"(?P<codigo>[^/]+)"
        r"/"
        r"(?P<departamento>[^/]+)"
        r"/"
        r"(?P<categoria>[^/]+)"
        r"/?$",
        flags=re.IGNORECASE,
    )

    correspondencia = padrao.match(
        caminho
    )

    if correspondencia is None:
        return None

    novo_caminho = (
        f"/{correspondencia.group('slug')}"
        f"/divulgador/oferta/"
        f"{correspondencia.group('codigo')}/"
        f"{correspondencia.group('departamento')}/"
        f"{correspondencia.group('categoria')}"
    )

    return urlunsplit(
        (
            partes.scheme or "https",
            f"www.{DOMINIO_MAGALU}",
            novo_caminho,
            "",
            "",
        )
    )


def gerar_urls_alternativas_magalu(
    url: str,
) -> list[str]:
    """
    Retorna versões alternativas oficiais conhecidas para uma URL
    do Magazine Luiza.
    """

    url_divulgador = (
        gerar_url_divulgador_magalu(
            url
        )
    )

    if url_divulgador is None:
        return []

    return [
        url_divulgador
    ]


__all__ = [
    "DOMINIO_MAGALU",
    "extrair_preco_magalu",
    "gerar_url_divulgador_magalu",
    "gerar_urls_alternativas_magalu",
]