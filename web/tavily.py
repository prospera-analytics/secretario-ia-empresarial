from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from dotenv import load_dotenv
from tavily import TavilyClient

from web.concorrentes import gerar_urls_alternativas
from web.concorrentes.amazon import (
    eh_dominio_amazon_brasil,
    normalizar_url_amazon,
)

load_dotenv()

_API_KEY = os.getenv("TAVILY_API_KEY")

if not _API_KEY:
    raise RuntimeError(
        "A variável TAVILY_API_KEY não foi encontrada."
    )


MAX_RESULTADOS_BUSCA = 8
MAX_PAGINAS_EXTRACAO = 8
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


def _normalizar_url_para_comparacao(
    url: str,
) -> str:
    """
    Normaliza a URL para comparação.

    Ignora:
    - protocolo;
    - prefixo www.;
    - query string;
    - fragmento;
    - barra final.
    """

    partes = urlsplit(
        url.strip()
    )

    dominio = partes.netloc.lower()

    if dominio.startswith("www."):
        dominio = dominio[4:]

    caminho = re.sub(
        r"/+",
        "/",
        partes.path,
    ).rstrip("/")

    return f"{dominio}{caminho}".lower()


def _normalizar_url_especifica_concorrente(
    url: str,
) -> str | None:
    """
    Aplica regras específicas de validação e normalização por loja.

    Para a Amazon Brasil:
    - aceita somente páginas individuais de produto;
    - rejeita páginas de busca e categorias;
    - normaliza a URL para /dp/<ASIN>.

    Para outros concorrentes, preserva a URL original.
    """
    url_limpa = url.strip()

    if not url_limpa:
        return None

    if eh_dominio_amazon_brasil(
        url_limpa
    ):
        return normalizar_url_amazon(
            url_limpa
        )

    return url_limpa


def _url_pertence_ao_dominio(
    url: str,
    dominio: str,
) -> bool:
    """Confirma se a URL pertence ao domínio solicitado."""

    dominio_normalizado = _normalizar_dominio(
        dominio
    )

    partes = urlsplit(
        url.strip()
    )

    dominio_url = partes.netloc.lower()

    if dominio_url.startswith("www."):
        dominio_url = dominio_url[4:]

    return (
        dominio_url == dominio_normalizado
        or dominio_url.endswith(
            f".{dominio_normalizado}"
        )
    )


def _conteudo_indica_bloqueio(
    conteudo: str,
) -> bool:
    """
    Detecta páginas de bloqueio que a API pode retornar como sucesso.
    """

    texto = conteudo.casefold()

    indicadores = (
        "erro 403",
        "error 403",
        "access denied",
        "acesso negado",
        "não é possível acessar a página",
        "nao e possivel acessar a pagina",
        "por favor, tente novamente em 1 minuto",
        "verify you are human",
        "verifique se você é humano",
        "captcha",
    )

    return any(
        indicador in texto
        for indicador in indicadores
    )


def _expandir_urls_especificas(
    candidatos: list[ResultadoBuscaWeb],
) -> list[ResultadoBuscaWeb]:
    """
    Acrescenta variações oficiais conhecidas das URLs encontradas.

    As regras específicas de cada loja ficam nos módulos da pasta
    web/concorrentes.
    """

    expandidos: list[ResultadoBuscaWeb] = []
    urls_adicionadas: set[str] = set()

    def adicionar(
        candidato: ResultadoBuscaWeb,
    ) -> None:
        url_normalizada = (
            _normalizar_url_especifica_concorrente(
                candidato.url
            )
        )

        if url_normalizada is None:
            return

        chave = _normalizar_url_para_comparacao(
            url_normalizada
        )

        if not chave:
            return

        if chave in urls_adicionadas:
            return

        urls_adicionadas.add(
            chave
        )

        expandidos.append(
            ResultadoBuscaWeb(
                titulo=candidato.titulo,
                url=url_normalizada,
                conteudo_resumo=(
                    candidato.conteudo_resumo
                ),
                pontuacao=candidato.pontuacao,
            )
        )

    for candidato in candidatos:
        adicionar(
            candidato
        )

        urls_alternativas = gerar_urls_alternativas(
            candidato.url
        )

        for url_alternativa in urls_alternativas:
            adicionar(
                ResultadoBuscaWeb(
                    titulo=candidato.titulo,
                    url=url_alternativa,
                    conteudo_resumo=(
                        candidato.conteudo_resumo
                    ),
                    pontuacao=max(
                        candidato.pontuacao - 0.001,
                        0.0,
                    ),
                )
            )

    return expandidos


def buscar_paginas_candidatas(
    nome_produto: str,
    nome_concorrente: str,
    dominio_concorrente: str,
    max_resultados: int = MAX_RESULTADOS_BUSCA,
) -> list[ResultadoBuscaWeb]:
    """
    Encontra páginas candidatas no domínio do concorrente.

    Esta função não interpreta preços e não acessa o banco.
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
        f'{nome_concorrente} '
        f'preço comprar'
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
    urls_adicionadas: set[str] = set()

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

        url_normalizada = (
            _normalizar_url_especifica_concorrente(
                url
            )
        )

        if url_normalizada is None:
            continue

        url = url_normalizada

        chave_url = _normalizar_url_para_comparacao(
            url
        )

        if chave_url in urls_adicionadas:
            continue

        urls_adicionadas.add(
            chave_url
        )

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
    Expande as URLs conhecidas e extrai o conteúdo em lote.

    Páginas bloqueadas, vazias ou não associadas a uma candidata são
    descartadas antes de chegar ao serviço de análise de preços.
    """

    if not candidatos:
        return []

    if max_paginas <= 0:
        raise ValueError(
            "max_paginas deve ser maior que zero."
        )

    candidatos_expandidos = (
        _expandir_urls_especificas(
            candidatos
        )
    )

    candidatos_ordenados = sorted(
        candidatos_expandidos,
        key=lambda item: item.pontuacao,
        reverse=True,
    )[:min(
        max_paginas,
        MAX_PAGINAS_EXTRACAO,
    )]

    urls = [
        candidato.url
        for candidato in candidatos_ordenados
    ]

    por_url_normalizada = {
        _normalizar_url_para_comparacao(
            candidato.url
        ): candidato
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
            format="text",
            include_images=False,
        )
    except TypeError:
        resposta = cliente_tavily.extract(
            urls=urls,
            extract_depth="advanced",
            format="text",
            include_images=False,
        )

    paginas: list[PaginaExtraida] = []
    paginas_adicionadas: set[str] = set()

    for resultado in resposta.get(
        "results",
        [],
    ):
        url_resultado = str(
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

        if not url_resultado:
            continue

        if not conteudo_extraido:
            continue

        if _conteudo_indica_bloqueio(
            conteudo_extraido
        ):
            continue

        chave_resultado = (
            _normalizar_url_para_comparacao(
                url_resultado
            )
        )

        candidato = por_url_normalizada.get(
            chave_resultado
        )

        if candidato is None:
            continue

        if chave_resultado in paginas_adicionadas:
            continue

        paginas_adicionadas.add(
            chave_resultado
        )

        paginas.append(
            PaginaExtraida(
                titulo=candidato.titulo,
                url=url_resultado,
                conteudo_resumo=(
                    candidato.conteudo_resumo
                ),
                conteudo_extraido=(
                    conteudo_extraido
                ),
                pontuacao_busca=(
                    candidato.pontuacao
                ),
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

    Novos serviços devem usar buscar_e_extrair_paginas().
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