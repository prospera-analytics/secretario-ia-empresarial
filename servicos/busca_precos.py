from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from sqlalchemy.orm import Session

from crud.concorrente import (
    listar_precos_concorrentes,
    registrar_preco_concorrente,
)
from database.models.concorrente import Concorrente
from database.models.preco_concorrente import PrecoConcorrente
from database.models.produto import Produto
from servicos.extracao_precos import (
    OfertaValidada,
    TipoCorrespondencia,
    analisar_oferta_produto,
)
from web.tavily import (
    PaginaExtraida,
    buscar_e_extrair_paginas,
)


HORAS_CACHE_PRECO = 24


@dataclass(frozen=True)
class ResultadoConsultaPreco:
    fonte: Literal["cache", "web"]
    produto_id: int
    produto_nome: str
    concorrente_id: int
    concorrente_nome: str
    preco: Decimal
    moeda: str
    titulo_encontrado: str
    url: str
    similaridade: Decimal
    tipo_correspondencia: TipoCorrespondencia
    coletado_em: datetime
    registro_preco: PrecoConcorrente
    diferencas: tuple[str, ...] = ()


def _obter_agora_compativel(
    data_referencia: datetime,
) -> datetime:
    if data_referencia.tzinfo is None:
        return datetime.now()

    return datetime.now(
        timezone.utc
    ).astimezone(
        data_referencia.tzinfo
    )


def _validar_produto(
    sessao: Session,
    produto_id: int,
) -> Produto:
    if produto_id <= 0:
        raise ValueError(
            "O ID do produto deve ser maior que zero."
        )

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    if not produto.ativo:
        raise ValueError(
            f"O produto '{produto.nome}' está desativado."
        )

    return produto


def _validar_concorrente(
    sessao: Session,
    concorrente_id: int,
) -> Concorrente:
    if concorrente_id <= 0:
        raise ValueError(
            "O ID do concorrente deve ser maior que zero."
        )

    concorrente = sessao.get(
        Concorrente,
        concorrente_id,
    )

    if concorrente is None:
        raise ValueError(
            f"Concorrente com ID {concorrente_id} não encontrado."
        )

    if not concorrente.ativo:
        raise ValueError(
            f"O concorrente '{concorrente.nome}' está desativado."
        )

    return concorrente


def _normalizar_texto(
    texto: str,
) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFKD",
            texto,
        )
        if not unicodedata.combining(
            caractere
        )
    ).lower()

    separado = re.sub(
        r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)",
        " ",
        sem_acentos,
    )

    return " ".join(
        re.sub(
            r"[^a-z0-9]+",
            " ",
            separado,
        ).split()
    )


def _montar_nome_produto_para_busca(
    produto: Produto,
) -> str:
    nome = produto.nome.strip()
    partes = [nome]

    nome_normalizado = _normalizar_texto(
        nome
    )

    marca_normalizada = _normalizar_texto(
        produto.marca
    )

    if marca_normalizada not in nome_normalizado:
        partes.insert(
            0,
            produto.marca.strip(),
        )

    if (
        str(produto.armazenamento_gb)
        not in nome_normalizado.split()
    ):
        partes.append(
            f"{produto.armazenamento_gb}GB"
        )

    return " ".join(
        partes
    )


def buscar_preco_recente_no_cache(
    sessao: Session,
    produto_id: int,
    concorrente_id: int,
    horas_cache: int = HORAS_CACHE_PRECO,
) -> PrecoConcorrente | None:
    if (
        produto_id <= 0
        or concorrente_id <= 0
    ):
        raise ValueError(
            "Os IDs devem ser maiores que zero."
        )

    if horas_cache <= 0:
        raise ValueError(
            "O período do cache deve ser maior que zero."
        )

    precos = listar_precos_concorrentes(
        sessao=sessao,
        produto_id=produto_id,
        concorrente_id=concorrente_id,
        apenas_disponiveis=True,
    )

    if not precos:
        return None

    registro = precos[0]

    if registro.coletado_em is None:
        return None

    limite = (
        _obter_agora_compativel(
            registro.coletado_em
        )
        - timedelta(
            hours=horas_cache
        )
    )

    if registro.coletado_em < limite:
        return None

    return registro


def _montar_resultado_cache(
    produto: Produto,
    concorrente: Concorrente,
    registro: PrecoConcorrente,
) -> ResultadoConsultaPreco:
    return ResultadoConsultaPreco(
        fonte="cache",
        produto_id=produto.id,
        produto_nome=produto.nome,
        concorrente_id=concorrente.id,
        concorrente_nome=concorrente.nome,
        preco=registro.preco,
        moeda=registro.moeda,
        titulo_encontrado=(
            registro.nome_produto_encontrado
        ),
        url=registro.url,
        similaridade=registro.similaridade,
        tipo_correspondencia=(
            registro.tipo_correspondencia
        ),
        coletado_em=registro.coletado_em,
        registro_preco=registro,
    )


def _selecionar_melhor_oferta(
    paginas: list[PaginaExtraida],
    produto: Produto,
    dominio_concorrente: str,
) -> tuple[
    PaginaExtraida,
    OfertaValidada,
] | None:
    """
    Analisa cada página e mantém no máximo uma oferta por página.
    """

    candidatas: list[
        tuple[
            PaginaExtraida,
            OfertaValidada,
        ]
    ] = []

    for pagina in paginas:
        oferta = analisar_oferta_produto(
            dominio=dominio_concorrente,
            titulo=pagina.titulo,
            conteudo=pagina.conteudo_extraido,
            nome_produto=produto.nome,
            marca=produto.marca,
            armazenamento_gb=(
                produto.armazenamento_gb
            ),
        )

        if oferta is None:
            continue

        candidatas.append(
            (
                pagina,
                oferta,
            )
        )

    if not candidatas:
        return None

    ordem_correspondencia = {
        "exato": 4,
        "equivalente": 3,
        "muito_similar": 2,
        "similar": 1,
    }

    return max(
        candidatas,
        key=lambda item: (
            ordem_correspondencia[
                item[1].correspondencia
            ],
            item[1].confianca,
            item[0].pontuacao_busca,
            -item[1].preco,
        ),
    )


def consultar_preco_produto_concorrente(
    sessao: Session,
    produto_id: int,
    concorrente_id: int,
    horas_cache: int = HORAS_CACHE_PRECO,
    forcar_atualizacao: bool = False,
) -> ResultadoConsultaPreco | None:
    """
    Consulta o preço de um produto em um concorrente.

    Fluxo:

    1. valida produto e concorrente;
    2. consulta o cache;
    3. busca e extrai páginas;
    4. valida o produto de cada página;
    5. extrai um único preço explícito por página;
    6. seleciona a melhor oferta válida;
    7. registra o resultado no banco.
    """

    produto = _validar_produto(
        sessao,
        produto_id,
    )

    concorrente = _validar_concorrente(
        sessao,
        concorrente_id,
    )

    if not forcar_atualizacao:
        cache = buscar_preco_recente_no_cache(
            sessao=sessao,
            produto_id=produto.id,
            concorrente_id=concorrente.id,
            horas_cache=horas_cache,
        )

        if cache is not None:
            return _montar_resultado_cache(
                produto=produto,
                concorrente=concorrente,
                registro=cache,
            )

    paginas = buscar_e_extrair_paginas(
        nome_produto=(
            _montar_nome_produto_para_busca(
                produto
            )
        ),
        nome_concorrente=concorrente.nome,
        dominio_concorrente=(
            concorrente.dominio
        ),
    )

    melhor = _selecionar_melhor_oferta(
        paginas=paginas,
        produto=produto,
        dominio_concorrente=(
            concorrente.dominio
        ),
    )

    if melhor is None:
        return None

    pagina, oferta = melhor

    similaridade = (
        oferta.confianca.quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
    )

    registro = registrar_preco_concorrente(
        sessao=sessao,
        produto_id=produto.id,
        concorrente_id=concorrente.id,
        nome_produto_encontrado=(
            pagina.titulo
        ),
        preco=oferta.preco,
        moeda=oferta.moeda,
        url=pagina.url,
        similaridade=similaridade,
        tipo_correspondencia=(
            oferta.correspondencia
        ),
        disponivel=True,
    )

    return ResultadoConsultaPreco(
        fonte="web",
        produto_id=produto.id,
        produto_nome=produto.nome,
        concorrente_id=concorrente.id,
        concorrente_nome=concorrente.nome,
        preco=registro.preco,
        moeda=registro.moeda,
        titulo_encontrado=(
            registro.nome_produto_encontrado
        ),
        url=registro.url,
        similaridade=registro.similaridade,
        tipo_correspondencia=(
            registro.tipo_correspondencia
        ),
        coletado_em=registro.coletado_em,
        registro_preco=registro,
        diferencas=oferta.diferencas,
    )


__all__ = [
    "HORAS_CACHE_PRECO",
    "ResultadoConsultaPreco",
    "buscar_preco_recente_no_cache",
    "consultar_preco_produto_concorrente",
]