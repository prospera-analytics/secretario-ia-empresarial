from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv()

_API_KEY = os.getenv("TAVILY_API_KEY")

if not _API_KEY:
    raise RuntimeError(
        "A variável TAVILY_API_KEY não foi encontrada."
    )


MAX_RESULTADOS_BUSCA = 8
MAX_PAGINAS_EXTRACAO = 5
PONTUACAO_MINIMA_RESULTADO = 0.35


cliente_tavily = TavilyClient(
    api_key=_API_KEY,
)


@dataclass(frozen=True)
class ResultadoBuscaWeb:
    """Página candidata encontrada pela Tavily Search."""

    titulo: str
    url: str
    conteudo_resumo: str
    pontuacao: float


@dataclass(frozen=True)
class PaginaExtraida:
    """Conteúdo integral ou relevante obtido pela Tavily Extract."""

    titulo: str
    url: str
    conteudo_resumo: str
    conteudo_extraido: str
    pontuacao_busca: float


def _normalizar_dominio(
    dominio: str,
) -> str:
    """Remove protocolo e barras para uso em include_domains."""

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


def _url_pertence_ao_dominio(
    url: str,
    dominio: str,
) -> bool:
    """Confirma se a URL pertence ao domínio solicitado."""

    dominio_normalizado = _normalizar_dominio(
        dominio
    )

    url_normalizada = url.strip().lower()

    return (
        f"://{dominio_normalizado}" in url_normalizada
        or f"://www.{dominio_normalizado}" in url_normalizada
    )


def buscar_paginas_candidatas(
    nome_produto: str,
    nome_concorrente: str,
    dominio_concorrente: str,
    max_resultados: int = MAX_RESULTADOS_BUSCA,
) -> list[ResultadoBuscaWeb]:
    """
    Encontra páginas candidatas no domínio do concorrente.

    Esta função não decide se a página é individual, não interpreta preço
    e não acessa o banco. A validação principal será feita posteriormente
    com o conteúdo obtido pela Tavily Extract.
    """

    if not nome_produto.strip():
        raise ValueError(
            "O nome do produto não pode estar vazio."
        )

    if not dominio_concorrente.strip():
        raise ValueError(
            "O domínio do concorrente não pode estar vazio."
        )

    if max_resultados <= 0:
        raise ValueError(
            "max_resultados deve ser maior que zero."
        )

    dominio_normalizado = _normalizar_dominio(
        dominio_concorrente
    )

    consulta = (
        f'"{nome_produto}" '
        f'"R$" '
        f'{nome_concorrente} '
        f'comprar'
    )

    resposta = cliente_tavily.search(
        query=consulta,
        topic="general",
        search_depth="basic",
        max_results=min(
            max_resultados,
            MAX_RESULTADOS_BUSCA,
        ),
        include_domains=[
            dominio_normalizado
        ],
        include_answer=False,
        include_raw_content=False,
        include_images=False,
        country="brazil",
    )

    candidatos: list[ResultadoBuscaWeb] = []

    for resultado in resposta.get(
        "results",
        [],
    ):
        titulo = str(
            resultado.get(
                "title",
                "",
            )
        ).strip()

        url = str(
            resultado.get(
                "url",
                "",
            )
        ).strip()

        conteudo = str(
            resultado.get(
                "content",
                "",
            )
        ).strip()

        try:
            pontuacao = float(
                resultado.get(
                    "score",
                    0,
                )
                or 0
            )
        except (TypeError, ValueError):
            pontuacao = 0.0

        if not titulo or not url:
            continue

        if pontuacao < PONTUACAO_MINIMA_RESULTADO:
            continue

        if not _url_pertence_ao_dominio(
            url=url,
            dominio=dominio_normalizado,
        ):
            continue

        candidatos.append(
            ResultadoBuscaWeb(
                titulo=titulo,
                url=url,
                conteudo_resumo=conteudo,
                pontuacao=pontuacao,
            )
        )

    return candidatos


def extrair_paginas_candidatas(
    candidatos: list[ResultadoBuscaWeb],
    nome_produto: str,
    max_paginas: int = MAX_PAGINAS_EXTRACAO,
) -> list[PaginaExtraida]:
    """
    Extrai em lote o conteúdo das páginas mais bem pontuadas.

    A chamada usa query para priorizar trechos relacionados ao produto.
    Há fallback para versões do SDK que ainda não aceitam query e
    chunks_per_source no método extract().
    """

    if not candidatos:
        return []

    if max_paginas <= 0:
        raise ValueError(
            "max_paginas deve ser maior que zero."
        )

    candidatos_ordenados = sorted(
        candidatos,
        key=lambda item: item.pontuacao,
        reverse=True,
    )[:min(max_paginas, MAX_PAGINAS_EXTRACAO)]

    urls = [
        candidato.url
        for candidato in candidatos_ordenados
    ]

    por_url = {
        candidato.url: candidato
        for candidato in candidatos_ordenados
    }

    try:
        resposta = cliente_tavily.extract(
            urls=urls,
            query=(
                f"{nome_produto} preço R$ "
                f"à vista Pix parcelado"
            ),
            chunks_per_source=5,
            extract_depth="advanced",
            format="markdown",
            include_images=False,
        )
    except TypeError:
        # Compatibilidade com versões anteriores do tavily-python.
        resposta = cliente_tavily.extract(
            urls=urls,
            extract_depth="advanced",
            format="markdown",
            include_images=False,
        )

    paginas: list[PaginaExtraida] = []

    for resultado in resposta.get(
        "results",
        [],
    ):
        url = str(
            resultado.get(
                "url",
                "",
            )
        ).strip()

        conteudo_extraido = str(
            resultado.get(
                "raw_content",
                "",
            )
            or ""
        ).strip()

        candidato = por_url.get(url)

        if candidato is None:
            continue

        if not conteudo_extraido:
            continue

        paginas.append(
            PaginaExtraida(
                titulo=candidato.titulo,
                url=candidato.url,
                conteudo_resumo=candidato.conteudo_resumo,
                conteudo_extraido=conteudo_extraido,
                pontuacao_busca=candidato.pontuacao,
            )
        )

    return paginas


def buscar_e_extrair_paginas(
    nome_produto: str,
    nome_concorrente: str,
    dominio_concorrente: str,
) -> list[PaginaExtraida]:
    """Executa Search e Extract sem interpretar ou persistir preços."""

    candidatos = buscar_paginas_candidatas(
        nome_produto=nome_produto,
        nome_concorrente=nome_concorrente,
        dominio_concorrente=dominio_concorrente,
    )

    return extrair_paginas_candidatas(
        candidatos=candidatos,
        nome_produto=nome_produto,
    )


def buscar_oferta_no_concorrente(
    nome_produto: str,
    nome_concorrente: str,
    dominio_concorrente: str,
) -> dict[str, Any] | None:
    """
    Função mantida por compatibilidade com código antigo.

    Retorna a primeira página extraída, mas novos serviços devem usar
    buscar_e_extrair_paginas() para avaliar todas as candidatas.
    """

    paginas = buscar_e_extrair_paginas(
        nome_produto=nome_produto,
        nome_concorrente=nome_concorrente,
        dominio_concorrente=dominio_concorrente,
    )

    if not paginas:
        return None

    pagina = paginas[0]

    return {
        "titulo": pagina.titulo,
        "url": pagina.url,
        "conteudo": pagina.conteudo_extraido,
        "conteudo_resumo": pagina.conteudo_resumo,
        "pontuacao": pagina.pontuacao_busca,
    }
