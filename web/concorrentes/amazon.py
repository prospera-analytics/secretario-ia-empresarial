from __future__ import annotations

import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from web.concorrentes import PrecoExtraido


_DOMINIOS_AMAZON_BR = {
    "amazon.com.br",
    "www.amazon.com.br",
}


_PADRAO_ASIN = re.compile(
    r"^[A-Z0-9]{10}$",
    flags=re.IGNORECASE,
)


_PADROES_CAMINHO_PRODUTO = (
    re.compile(
        r"/dp/([A-Z0-9]{10})(?:[/?#]|$)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"/gp/product/([A-Z0-9]{10})(?:[/?#]|$)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"/gp/aw/d/([A-Z0-9]{10})(?:[/?#]|$)",
        flags=re.IGNORECASE,
    ),
)


_VALOR_BRL_NUMERICO = (
    r"\d{1,3}"
    r"(?:\.\d{3})*"
    r",\d{2}"
)


_PADRAO_PRECO_A_VISTA_AMAZON = re.compile(
    rf"""
    R\$\s*
    (?P<valor>{_VALOR_BRL_NUMERICO})

    (?:
        \s*
        R\$\s*
        (?P=valor)
    )?

    \s*
    (?:à|a)\s+vista\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


_PADRAO_PRECO_TOTAL_AMAZON = re.compile(
    rf"""
    (?:ou\s*)?

    R\$\s*
    (?P<valor>{_VALOR_BRL_NUMERICO})

    \s*
    em\s+at[eé]\s+
    \d{{1,2}}\s*x\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


_PADRAO_PRECO_TOTAL_TABELA_AMAZON = re.compile(
    rf"""
    (?:^|\n)
    \s*
    \|?
    \s*

    em\s+
    \d{{1,2}}\s*x

    \s*
    (?:de\s*)?

    R\$\s*
    (?P<parcela>{_VALOR_BRL_NUMERICO})

    \s*
    (?:sem\s+juros)?

    \s*
    \|

    \s*
    R\$\s*
    (?P<valor>{_VALOR_BRL_NUMERICO})

    \s*
    \|?
    """,
    flags=(
        re.IGNORECASE
        | re.VERBOSE
        | re.MULTILINE
    ),
)


def _converter_valor_brl(
    valor: str,
) -> Decimal | None:
    """
    Converte um valor brasileiro para Decimal.

    Exemplo:

    6.119,10 -> Decimal("6119.10")
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
    Converte o grupo nomeado 'valor' de um regex
    em PrecoExtraido.
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


def extrair_preco_amazon(
    conteudo: str,
) -> PrecoExtraido | None:
    """
    Extrai no máximo um preço explícito da Amazon.

    Prioridade:

    1. preço explicitamente associado a "à vista";
    2. preço total seguido por "em até Nx";
    3. preço total apresentado na segunda coluna da
       tabela de parcelamento.

    Exemplo de tabela reconhecida:

    | Em 2x de R$ 2.721,67 sem juros | R$ 5.443,33 |

    Nesse exemplo:

    - R$ 2.721,67 é a parcela;
    - R$ 5.443,33 é o total explícito.

    O extrator não:

    - multiplica parcelas;
    - calcula descontos;
    - captura seguros;
    - captura acessórios;
    - usa preço anterior isolado;
    - infere valores ausentes.
    """

    if not isinstance(
        conteudo,
        str,
    ):
        return None

    conteudo = conteudo.strip()

    if not conteudo:
        return None

    resultado_a_vista = (
        _PADRAO_PRECO_A_VISTA_AMAZON.search(
            conteudo
        )
    )

    preco_a_vista = _criar_preco_extraido(
        resultado=resultado_a_vista,
        modalidade="avista",
    )

    if preco_a_vista is not None:
        return preco_a_vista

    resultado_total = (
        _PADRAO_PRECO_TOTAL_AMAZON.search(
            conteudo
        )
    )

    preco_total = _criar_preco_extraido(
        resultado=resultado_total,
        modalidade="preco_total",
    )

    if preco_total is not None:
        return preco_total

    resultado_tabela = (
        _PADRAO_PRECO_TOTAL_TABELA_AMAZON.search(
            conteudo
        )
    )

    return _criar_preco_extraido(
        resultado=resultado_tabela,
        modalidade="preco_total",
    )


def eh_dominio_amazon_brasil(
    url: str,
) -> bool:
    """
    Verifica se a URL pertence à Amazon Brasil.

    Somente estes domínios são aceitos:

    - amazon.com.br
    - www.amazon.com.br
    """

    if not isinstance(
        url,
        str,
    ):
        return False

    url = url.strip()

    if not url:
        return False

    try:
        dominio = (
            urlparse(url).hostname
            or ""
        ).lower()
    except ValueError:
        return False

    return dominio in _DOMINIOS_AMAZON_BR


def extrair_asin_amazon(
    url: str,
) -> str | None:
    """
    Extrai o ASIN de uma página individual de produto.

    Formatos aceitos:

    - /dp/<ASIN>
    - /gp/product/<ASIN>
    - /gp/aw/d/<ASIN>

    Páginas de busca, categorias e URLs sem ASIN retornam None.
    """

    if not eh_dominio_amazon_brasil(
        url
    ):
        return None

    try:
        caminho = urlparse(
            url.strip()
        ).path
    except ValueError:
        return None

    for padrao in _PADROES_CAMINHO_PRODUTO:
        resultado = padrao.search(
            caminho
        )

        if resultado is None:
            continue

        asin = resultado.group(
            1
        ).upper()

        if _PADRAO_ASIN.fullmatch(
            asin
        ):
            return asin

    return None


def eh_url_produto_amazon(
    url: str,
) -> bool:
    """
    Retorna True apenas para páginas individuais
    de produto da Amazon Brasil.
    """

    return (
        extrair_asin_amazon(url)
        is not None
    )


def normalizar_url_amazon(
    url: str,
) -> str | None:
    """
    Converte uma URL de produto para o formato canônico.

    Entrada:

    https://www.amazon.com.br/Apple-iPhone-16/dp/B0DJFTJ6LX?tag=teste

    Saída:

    https://www.amazon.com.br/dp/B0DJFTJ6LX
    """

    asin = extrair_asin_amazon(
        url
    )

    if asin is None:
        return None

    return (
        "https://www.amazon.com.br/"
        f"dp/{asin}"
    )


def filtrar_urls_produto_amazon(
    urls: Iterable[str],
) -> list[str]:
    """
    Mantém somente URLs individuais de produtos
    da Amazon Brasil.

    Também:

    - normaliza as URLs;
    - remove parâmetros de rastreamento;
    - remove URLs duplicadas;
    - preserva a ordem original.
    """

    urls_validas: list[str] = []
    urls_vistas: set[str] = set()

    for url in urls:
        url_normalizada = (
            normalizar_url_amazon(
                url
            )
        )

        if url_normalizada is None:
            continue

        if url_normalizada in urls_vistas:
            continue

        urls_vistas.add(
            url_normalizada
        )

        urls_validas.append(
            url_normalizada
        )

    return urls_validas


# Aliases temporários para compatibilidade.
eh_url_amazon = eh_url_produto_amazon
extrair_asin = extrair_asin_amazon
normalizar_url = normalizar_url_amazon


__all__ = [
    "extrair_preco_amazon",
    "eh_dominio_amazon_brasil",
    "eh_url_produto_amazon",
    "eh_url_amazon",
    "extrair_asin_amazon",
    "extrair_asin",
    "normalizar_url_amazon",
    "normalizar_url",
    "filtrar_urls_produto_amazon",
]