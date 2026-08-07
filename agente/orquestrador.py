"""
Orquestração determinística dos fluxos empresariais críticos.

Este módulo executa diretamente os fluxos conhecidos, sem depender
do modelo para escolher ferramentas, interpretar resultados ou
realizar cálculos empresariais simples.
"""

from __future__ import annotations

import re

import unicodedata
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal, Mapping

from analises.margem import (
    analisar_margem_produto,
)

from crud.concorrente import (
    listar_concorrentes,
    listar_precos_concorrentes,
    buscar_menor_preco_concorrente,
)

from crud.produto import listar_produtos
from database.models.preco_concorrente import (
    PrecoConcorrente,
)

from database.conexao import SessionLocal
from agente.contexto import (
    ContextoResolvido,
    resolver_contexto,
)
from agente.memoria import (
    normalizar_memoria,
    registrar_comparacao,
    registrar_concorrente,
    registrar_fluxo,
    registrar_oferta,
    registrar_produto,
)
from servicos.busca_precos import (
    consultar_preco_produto_concorrente,
)


TipoFluxo = Literal[
    "listar_produtos",
    "consultar_preco_interno",
    "consultar_preco_concorrente",
    "comparar_preco_concorrente",
    "comparar_catalogo_concorrentes",
    "listar_produtos_equivalentes",
    "filtrar_comparacoes_catalogo",
    "avaliar_reducao_preco",
]


@dataclass(frozen=True)
class ResultadoOrquestracao:
    """
    Resultado de um fluxo executado sem decisão do LLM.
    """

    tratado: bool
    resposta: str | None
    memoria: dict[str, Any]
    fluxo: TipoFluxo | None = None
    dados: dict[str, Any] | None = None


_TERMOS_LISTAGEM = {
    "liste",
    "listar",
    "mostre",
    "mostrar",
    "quais temos",
    "catalogo",
    "catalogo de produtos",
}


_TERMOS_PRODUTO = {
    "produto",
    "produtos",
    "smartphone",
    "smartphones",
    "celular",
    "celulares",
    "catalogo",
}


_TERMOS_PRECO = {
    "preco",
    "precos",
    "valor",
    "valores",
    "custa",
    "custando",
    "quanto custa",
    "quanto esta",
    "oferta",
}

_TERMOS_REPETICAO = {
    "novamente",
    "de novo",
    "outra vez",
    "repita",
    "repetir",
    "refaca",
    "faca novamente",
}


_TERMOS_NOS_MAIS_BARATOS = {
    "mais baratos",
    "mais barato",
    "onde somos mais baratos",
    "onde estamos mais baratos",
    "so os mais baratos",
    "apenas os mais baratos",
    "precos mais baixos",
}


_TERMOS_NOS_MAIS_CAROS = {
    "mais caros",
    "mais caro",
    "onde somos mais caros",
    "onde estamos mais caros",
    "so os mais caros",
    "apenas os mais caros",
    "precos mais altos",
}


_PREFIXOS_CONTINUACAO_ENTIDADE = (
    "e na ",
    "e no ",
    "e o ",
    "e a ",
    "e com ",
    "agora na ",
    "agora no ",
    "agora o ",
    "agora a ",
)


_FLUXOS_REPETIVEIS = {
    "consultar_preco_interno",
    "consultar_preco_concorrente",
    "comparar_preco_concorrente",
    "comparar_catalogo_concorrentes",
    "listar_produtos_equivalentes",
}


_TERMOS_COMPARACAO = {
    "compare",
    "comparar",
    "comparacao",
    "se compara",
    "comparado",
    "diferenca",
    "mais barato",
    "mais caro",
    "nosso preco",
    "nosso produto",
    "nossa loja",
}


_TERMOS_ATUALIZACAO = {
    "atualize",
    "atualizar",
    "atualizado",
    "atualizada",
    "agora",
    "novo preco",
    "preco novo",
    "consulta nova",
}

_TERMOS_CATALOGO_COMPLETO = {
    "todos os produtos",
    "todos nossos produtos",
    "todos os nossos produtos",
    "nossos produtos",
    "nossos precos",
    "todos os precos",
    "catalogo",
    "catalogo inteiro",
}


_TERMOS_ESCOPO_GLOBAL_PRODUTOS = {
    "algum produto",
    "alguns produtos",
    "qual produto",
    "quais produtos",
    "existe algum produto",
    "existe produto",
    "entre nossos produtos",
    "entre os nossos produtos",
    "do nosso catalogo",
    "no nosso catalogo",
}

_TERMOS_EQUIVALENCIA = {
    "em comum",
    "comuns",
    "equivalente",
    "equivalentes",
    "mesmos produtos",
    "produtos iguais",
    "produtos semelhantes",
    "tambem vende",
    "tambem possui",
}


_TERMOS_PRECO_INTERNO = {
    "nosso preco",
    "preco interno",
    "preco da nossa loja",
    "preco em nossa loja",
    "quanto cobramos",
    "quanto vendemos",
    "nosso valor",
    "catalogo",
}

_TERMOS_DECISAO_REDUCAO_PRECO = {
    "vale a pena reduzir nosso preco",
    "vale a pena baixar nosso preco",
    "devemos reduzir nosso preco",
    "devemos baixar nosso preco",
    "deveriamos reduzir nosso preco",
    "deveriamos baixar nosso preco",
    "podemos reduzir nosso preco",
    "podemos baixar nosso preco",
    "compensa reduzir nosso preco",
    "compensa baixar nosso preco",
    "igualar o preco",
    "acompanhar o preco do concorrente",
    "reduzir o preco para competir",
    "baixar o preco para competir",
}


_TERMOS_REDUCAO_PRECO = {
    "reduzir",
    "baixar",
    "diminuir",
    "desconto",
    "igualar",
    "acompanhar",
}


_TERMOS_DECISAO_PRECO = {
    "vale a pena",
    "devemos",
    "deveriamos",
    "podemos",
    "compensa",
    "recomenda",
    "recomendaria",
}

def normalizar_texto(
    texto: str,
) -> str:
    """
    Normaliza texto para as regras determinísticas.

    - remove acentos;
    - converte ç para c;
    - remove pontuação;
    - separa números de letras.

    Exemplos:

    128GB -> 128 gb
    preço -> preco
    "E na Amazon?" -> "e na amazon"
    """

    texto = texto.replace(
        "ç",
        "c",
    ).replace(
        "Ç",
        "C",
    )

    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFKD",
            texto,
        )
        if not unicodedata.combining(
            caractere
        )
    )

    separado = re.sub(
        r"(?<=\d)(?=[a-zA-Z])|(?<=[a-zA-Z])(?=\d)",
        " ",
        sem_acentos,
    )

    return " ".join(
        re.sub(
            r"[^a-zA-Z0-9]+",
            " ",
            separado.lower(),
        ).split()
    )


def _contem_algum(
    texto: str,
    termos: set[str],
) -> bool:
    return any(
        termo in texto
        for termo in termos
    )

def _eh_decisao_reducao_preco(
    texto: str,
    memoria: Mapping[str, Any] | None,
) -> bool:
    """
    Detecta uma continuação que pede decisão sobre redução de preço.

    O fluxo somente é aceito quando existe uma comparação concorrencial
    confirmada na memória.
    """

    if not isinstance(memoria, Mapping):
        return False

    comparacao = memoria.get(
        "ultima_comparacao"
    )

    if not isinstance(comparacao, Mapping):
        return False

    produto_id = comparacao.get(
        "produto_id"
    )

    preco_interno = comparacao.get(
        "preco_interno"
    )

    preco_concorrente = comparacao.get(
        "preco_concorrente"
    )

    possui_comparacao_valida = (
        isinstance(produto_id, int)
        and produto_id > 0
        and isinstance(
            preco_interno,
            (int, float),
        )
        and isinstance(
            preco_concorrente,
            (int, float),
        )
    )

    if not possui_comparacao_valida:
        return False

    if _contem_algum(
        texto,
        _TERMOS_DECISAO_REDUCAO_PRECO,
    ):
        return True

    possui_reducao = _contem_algum(
        texto,
        _TERMOS_REDUCAO_PRECO,
    )

    possui_decisao = _contem_algum(
        texto,
        _TERMOS_DECISAO_PRECO,
    )

    menciona_preco = (
        "preco" in texto
        or "valor" in texto
    )

    return (
        possui_reducao
        and possui_decisao
        and menciona_preco
    )


def _obter_ultimo_fluxo(
    memoria: Mapping[str, Any] | None,
) -> str | None:
    """
    Retorna o último fluxo confirmado pela memória.
    """

    if not isinstance(
        memoria,
        Mapping,
    ):
        return None

    ultimo_fluxo = memoria.get(
        "ultimo_fluxo"
    )

    if (
        not isinstance(ultimo_fluxo, str)
        or not ultimo_fluxo.strip()
    ):
        return None

    return ultimo_fluxo.strip()


def _eh_continuacao_entidade(
    texto: str,
) -> bool:
    """
    Identifica perguntas curtas que alteram apenas uma entidade.

    Exemplos:

    - E na Magazine Luiza?
    - E o iPhone Pro?
    - Agora na Amazon.
    """

    return texto.startswith(
        _PREFIXOS_CONTINUACAO_ENTIDADE
    )

def detectar_fluxo(
    pergunta: str,
    contexto: ContextoResolvido | None = None,
    memoria: Mapping[str, Any] | None = None,
) -> TipoFluxo | None:
    """
    Detecta fluxos determinísticos em ordem de especificidade.

    A memória permite continuar uma operação anterior sem enviar
    o histórico inteiro ao modelo.
    """

    texto = normalizar_texto(
        pergunta
    )

    ultimo_fluxo = _obter_ultimo_fluxo(
        memoria
    )

    possui_comparacao = _contem_algum(
        texto,
        _TERMOS_COMPARACAO,
    )

    possui_preco = _contem_algum(
        texto,
        _TERMOS_PRECO,
    )

    possui_listagem = _contem_algum(
        texto,
        _TERMOS_LISTAGEM,
    )

    possui_produto = _contem_algum(
        texto,
        _TERMOS_PRODUTO,
    )

    possui_catalogo_completo = _contem_algum(
        texto,
        _TERMOS_CATALOGO_COMPLETO,
    )
    
    possui_escopo_global_produtos = _contem_algum(
        texto,
        _TERMOS_ESCOPO_GLOBAL_PRODUTOS,
    )

    possui_equivalencia = _contem_algum(
        texto,
        _TERMOS_EQUIVALENCIA,
    )

    possui_preco_interno = _contem_algum(
        texto,
        _TERMOS_PRECO_INTERNO,
    )
    
    possui_reducao_preco = _contem_algum(
        texto,
        _TERMOS_REDUCAO_PRECO,
    )

    possui_decisao_preco = _contem_algum(
        texto,
        _TERMOS_DECISAO_PRECO,
    )

    possui_reducao_preco = _contem_algum(
    texto,
    _TERMOS_REDUCAO_PRECO,
    )

    possui_decisao_preco = _contem_algum(
        texto,
        _TERMOS_DECISAO_PRECO,
    )
    
    pediu_repeticao = _contem_algum(
        texto,
        _TERMOS_REPETICAO,
    )

    pediu_mais_baratos = _contem_algum(
        texto,
        _TERMOS_NOS_MAIS_BARATOS,
    )

    pediu_mais_caros = _contem_algum(
        texto,
        _TERMOS_NOS_MAIS_CAROS,
    )

    tem_produto_resolvido = (
        contexto is not None
        and contexto.produto is not None
    )

    tem_concorrente_resolvido = (
        contexto is not None
        and contexto.concorrente is not None
    )


    if (
        _eh_decisao_reducao_preco(
            texto=texto,
            memoria=memoria,
        )
        or (
            tem_produto_resolvido
            and possui_reducao_preco
            and possui_decisao_preco
            and possui_preco
        )
    ):
        return "avaliar_reducao_preco"

    # Continuação de uma comparação ampla:
    # “Mostre só onde somos mais baratos.”
    if (
        pediu_mais_baratos
        or pediu_mais_caros
    ) and (
        possui_escopo_global_produtos
        or possui_catalogo_completo
        or ultimo_fluxo in {
            "comparar_catalogo_concorrentes",
            "filtrar_comparacoes_catalogo",
        }
    ):
        return "filtrar_comparacoes_catalogo"

    # “Quais produtos temos em comum com a Amazon?”
    if (
        possui_equivalencia
        and tem_concorrente_resolvido
    ):
        return "listar_produtos_equivalentes"

    # “Como nossos preços se comparam aos concorrentes?”
    if (
        possui_comparacao
        and (
            possui_catalogo_completo
            or not tem_produto_resolvido
        )
    ):
        return "comparar_catalogo_concorrentes"

    # “Como ele se compara com nosso produto?”
    if (
        possui_comparacao
        and tem_produto_resolvido
        and tem_concorrente_resolvido
    ):
        return "comparar_preco_concorrente"

    # “Qual é nosso preço do iPhone?”
    if (
        possui_preco
        and tem_produto_resolvido
        and not tem_concorrente_resolvido
        and (
            possui_preco_interno
            or "nosso" in texto
            or "nossa loja" in texto
        )
    ):
        return "consultar_preco_interno"

    # “Qual é o preço do iPhone na Amazon?”
    if (
        possui_preco
        and tem_produto_resolvido
        and tem_concorrente_resolvido
    ):
        return "consultar_preco_concorrente"

    # “E na Magazine Luiza?”
    # “E o iPhone Pro?”
    if (
        _eh_continuacao_entidade(
            texto
        )
        and tem_produto_resolvido
        and tem_concorrente_resolvido
        and ultimo_fluxo in {
            "consultar_preco_concorrente",
            "comparar_preco_concorrente",
        }
    ):
        return ultimo_fluxo

    # “Faça novamente.”
    # “De novo.”
    if (
        pediu_repeticao
        and ultimo_fluxo in _FLUXOS_REPETIVEIS
    ):
        return ultimo_fluxo

    # “Liste nossos produtos.”
    if (
        possui_listagem
        and possui_produto
    ):
        return "listar_produtos"

    return None


def _formatar_brl(
    valor: Decimal | float | int,
) -> str:
    """
    Formata um número no padrão monetário brasileiro.
    """

    decimal = Decimal(
        str(valor)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    texto = f"{decimal:,.2f}"

    texto = (
        texto
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )

    return f"R$ {texto}"

def _formatar_brl_markdown(
    valor: Decimal | float | int,
) -> str:
    """
    Formata moeda brasileira escapando o cifrão para Markdown.

    Use em frases corridas que podem conter mais de um valor monetário,
    evitando que o Streamlit interprete o trecho entre cifrões como LaTeX.
    """

    return _formatar_brl(
        valor
    ).replace(
        "$",
        r"\$",
    )

def _formatar_percentual(
    valor: Decimal,
) -> str:
    decimal = valor.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return (
        f"{decimal:.2f}"
        .replace(".", ",")
        + "%"
    )


def _formatar_data(
    valor: Any,
) -> str | None:
    if valor is None:
        return None

    texto = str(
        valor
    )

    try:
        data, horario = texto.split(
            "T",
            maxsplit=1,
        )

        ano, mes, dia = data.split(
            "-"
        )

        horario = horario[:5]

        return (
            f"{dia}/{mes}/{ano} "
            f"às {horario}"
        )

    except ValueError:
        return texto


def _listar_produtos() -> tuple[
    str,
    dict[str, Any],
]:
    """
    Consulta e formata o catálogo diretamente.
    """

    with SessionLocal() as sessao:
        produtos = listar_produtos(
            sessao=sessao,
            apenas_ativos=True,
        )

    if not produtos:
        return (
            "Não há produtos ativos cadastrados.",
            {
                "quantidade": 0,
                "produtos": [],
            },
        )

    linhas = [
        "Produtos ativos cadastrados:",
        "",
    ]

    dados_produtos: list[
        dict[str, Any]
    ] = []

    for indice, produto in enumerate(
        produtos,
        start=1,
    ):
        preco = _formatar_brl(
            produto.preco_venda
        )

        linhas.append(
            f"{indice}. **{produto.nome}** — {preco}"
        )

        dados_produtos.append(
            {
                "id": produto.id,
                "nome": produto.nome,
                "marca": produto.marca,
                "armazenamento_gb": (
                    produto.armazenamento_gb
                ),
                "preco_venda": float(
                    produto.preco_venda
                ),
                "ativo": produto.ativo,
            }
        )

    return (
        "\n".join(linhas),
        {
            "quantidade": len(
                dados_produtos
            ),
            "produtos": dados_produtos,
        },
    )


def _consultar_oferta(
    contexto: ContextoResolvido,
    forcar_atualizacao: bool,
) -> dict[str, Any] | None:
    """
    Executa o serviço real de preço concorrente.
    """

    if not contexto.completo_para_preco_concorrente:
        return None

    produto = contexto.produto
    concorrente = contexto.concorrente

    assert produto is not None
    assert concorrente is not None

    with SessionLocal() as sessao:
        try:
            resultado = (
                consultar_preco_produto_concorrente(
                    sessao=sessao,
                    produto_id=produto["id"],
                    concorrente_id=(
                        concorrente["id"]
                    ),
                    forcar_atualizacao=(
                        forcar_atualizacao
                    ),
                )
            )

            if resultado is None:
                sessao.rollback()
                return None

            sessao.commit()

            return {
                "fonte": resultado.fonte,
                "produto_id": resultado.produto_id,
                "produto_nome": resultado.produto_nome,
                "concorrente_id": (
                    resultado.concorrente_id
                ),
                "concorrente_nome": (
                    resultado.concorrente_nome
                ),
                "produto_encontrado": (
                    resultado.titulo_encontrado
                ),
                "preco": float(
                    resultado.preco
                ),
                "moeda": resultado.moeda,
                "correspondencia": (
                    resultado.tipo_correspondencia
                ),
                "similaridade": float(
                    resultado.similaridade
                ),
                "url": resultado.url,
                "coletado_em": (
                    resultado.coletado_em.isoformat()
                    if resultado.coletado_em
                    is not None
                    else None
                ),
                "diferencas": list(
                    resultado.diferencas
                ),
            }

        except Exception:
            sessao.rollback()
            raise


def _resposta_oferta(
    oferta: Mapping[str, Any],
) -> str:
    data = _formatar_data(
        oferta.get("coletado_em")
    )

    linhas = [
        f"**{oferta['concorrente_nome']}**",
        "",
        (
            f"- Produto encontrado: "
            f"{oferta['produto_encontrado']}"
        ),
        (
            f"- Preço: "
            f"{_formatar_brl(oferta['preco'])}"
        ),
        (
            f"- Correspondência: "
            f"{oferta['correspondencia']}"
        ),
    ]

    if data:
        linhas.append(
            f"- Coletado em: {data}"
        )

    if oferta.get("url"):
        linhas.append(
            f"- URL da oferta: {oferta['url']}"
        )
    else:
        linhas.append(
            "- URL da oferta não disponível."
        )

    return "\n".join(
        linhas
    )


def _comparar_precos(
    contexto: ContextoResolvido,
    oferta: Mapping[str, Any],
) -> tuple[
    str,
    dict[str, Any],
]:
    produto = contexto.produto
    concorrente = contexto.concorrente

    assert produto is not None
    assert concorrente is not None

    preco_interno = Decimal(
        str(produto["preco_venda"])
    )

    preco_concorrente = Decimal(
        str(oferta["preco"])
    )

    diferenca = (
        preco_interno
        - preco_concorrente
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if preco_concorrente != 0:
        percentual = (
            diferenca
            / preco_concorrente
            * Decimal("100")
        )
    else:
        percentual = Decimal("0")

    if diferenca > 0:
        conclusao = (
            f"Nosso preço está "
            f"{_formatar_brl(diferenca)} "
            f"({_formatar_percentual(percentual)}) "
            f"acima do preço da "
            f"{concorrente['nome']}."
        )

    elif diferenca < 0:
        diferenca_absoluta = abs(
            diferenca
        )

        percentual_absoluto = abs(
            percentual
        )

        conclusao = (
            f"Nosso preço está "
            f"{_formatar_brl(diferenca_absoluta)} "
            f"({_formatar_percentual(percentual_absoluto)}) "
            f"abaixo do preço da "
            f"{concorrente['nome']}."
        )

    else:
        conclusao = (
            "Nosso preço é igual ao preço "
            f"da {concorrente['nome']}."
        )

    data = _formatar_data(
        oferta.get("coletado_em")
    )

    linhas = [
        f"**{produto['nome']}**",
        "",
        (
            f"- Nosso preço: "
            f"{_formatar_brl(preco_interno)}"
        ),
        (
            f"- {concorrente['nome']}: "
            f"{_formatar_brl(preco_concorrente)}"
        ),
        (
            f"- Correspondência: "
            f"{oferta['correspondencia']}"
        ),
        "",
        conclusao,
    ]

    if data:
        linhas.extend(
        [
            "",
            f"- Coletado em: {data}",
        ]
    )

    if oferta.get("url"):
        linhas.append(
        f"- URL da oferta: {oferta['url']}"
        )

    dados = {
        "produto_id": produto["id"],
        "produto_nome": produto["nome"],
        "concorrente_id": concorrente["id"],
        "concorrente_nome": (
            concorrente["nome"]
        ),
        "preco_interno": float(
            preco_interno
        ),
        "preco_concorrente": float(
            preco_concorrente
        ),
        "diferenca_valor": float(
            diferenca
        ),
        "diferenca_percentual": float(
            percentual.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        ),
        "url": oferta.get("url"),
        "coletado_em": oferta.get(
            "coletado_em"
        ),
    }

    return (
        "\n".join(linhas),
        dados,
    )


def _oferta_cache_para_dict(
    oferta: PrecoConcorrente,
) -> dict[str, Any]:
    """
    Converte uma oferta persistida em estrutura independente
    da sessão SQLAlchemy.
    """

    produto = oferta.produto
    concorrente = oferta.concorrente

    return {
        "id": oferta.id,
        "produto_id": oferta.produto_id,
        "produto_nome": (
            produto.nome
            if produto is not None
            else None
        ),
        "preco_interno": (
            float(produto.preco_venda)
            if produto is not None
            else None
        ),
        "concorrente_id": oferta.concorrente_id,
        "concorrente_nome": (
            concorrente.nome
            if concorrente is not None
            else None
        ),
        "concorrente_dominio": (
            concorrente.dominio
            if concorrente is not None
            else None
        ),
        "produto_encontrado": (
            oferta.nome_produto_encontrado
        ),
        "preco": float(
            oferta.preco
        ),
        "moeda": oferta.moeda,
        "correspondencia": (
            oferta.tipo_correspondencia
        ),
        "similaridade": float(
            oferta.similaridade
        ),
        "url": oferta.url,
        "coletado_em": (
            oferta.coletado_em.isoformat()
            if oferta.coletado_em is not None
            else None
        ),
        "disponivel": oferta.disponivel,
    }


def _obter_ofertas_mais_recentes(
    concorrente_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Retorna apenas a oferta disponível mais recente para cada
    combinação de produto e concorrente.

    Nenhuma busca web é executada.
    """

    with SessionLocal() as sessao:
        ofertas = listar_precos_concorrentes(
            sessao=sessao,
            concorrente_id=concorrente_id,
            apenas_disponiveis=True,
        )

        ofertas_convertidas = [
            _oferta_cache_para_dict(
                oferta
            )
            for oferta in ofertas
        ]

    resultado: list[dict[str, Any]] = []
    combinacoes_vistas: set[
        tuple[int, int]
    ] = set()

    ofertas_convertidas.sort(
        key=lambda item: (
            item.get("coletado_em") or ""
        ),
        reverse=True,
    )

    for oferta in ofertas_convertidas:
        chave = (
            oferta["produto_id"],
            oferta["concorrente_id"],
        )

        if chave in combinacoes_vistas:
            continue

        combinacoes_vistas.add(
            chave
        )

        resultado.append(
            oferta
        )

    return resultado

def _consultar_preco_interno(
    contexto: ContextoResolvido,
) -> tuple[str, dict[str, Any]]:
    """
    Retorna diretamente o preço cadastrado do produto.
    """

    produto = contexto.produto

    assert produto is not None

    preco = produto.get(
        "preco_venda"
    )

    if preco is None:
        return (
            (
                f"O produto **{produto['nome']}** está cadastrado, "
                "mas não possui preço de venda disponível."
            ),
            {
                "produto": produto,
                "preco_disponivel": False,
            },
        )

    resposta = (
        f"**{produto['nome']}**\n\n"
        f"- Preço em nossa loja: "
        f"{_formatar_brl(preco)}"
    )

    return (
        resposta,
        {
            "produto": produto,
            "preco_disponivel": True,
            "preco": preco,
        },
    )

def _coletar_ofertas_catalogo() -> dict[str, Any]:
    """
    Completa os preços concorrentes do catálogo.

    Para cada combinação entre produto e concorrente ativo:

    - reutiliza uma oferta recente do cache, quando existir;
    - consulta a web quando não houver cache válido;
    - valida a correspondência do produto;
    - salva no banco somente ofertas verificáveis;
    - mantém o processamento mesmo quando uma busca falhar.

    Atualmente, com 10 produtos e 2 concorrentes, são analisadas
    no máximo 20 combinações. As consultas com cache não geram
    nova busca externa.
    """

    with SessionLocal() as sessao:
        produtos = listar_produtos(
            sessao=sessao,
            apenas_ativos=True,
        )

        concorrentes = listar_concorrentes(
            sessao=sessao,
            apenas_ativos=True,
        )

        # Copiamos somente os dados necessários para que rollbacks
        # durante uma busca não afetem os objetos SQLAlchemy.
        produtos_dados = [
            {
                "id": produto.id,
                "nome": produto.nome,
            }
            for produto in produtos
        ]

        concorrentes_dados = [
            {
                "id": concorrente.id,
                "nome": concorrente.nome,
                "dominio": concorrente.dominio,
            }
            for concorrente in concorrentes
        ]

        ofertas_cache: list[dict[str, Any]] = []
        ofertas_web: list[dict[str, Any]] = []
        nao_encontradas: list[dict[str, Any]] = []
        falhas: list[dict[str, Any]] = []

        for produto in produtos_dados:
            for concorrente in concorrentes_dados:
                try:
                    resultado = (
                        consultar_preco_produto_concorrente(
                            sessao=sessao,
                            produto_id=produto["id"],
                            concorrente_id=(
                                concorrente["id"]
                            ),
                            forcar_atualizacao=False,
                        )
                    )

                    if resultado is None:
                        sessao.rollback()

                        nao_encontradas.append(
                            {
                                "produto_id": produto["id"],
                                "produto_nome": produto["nome"],
                                "concorrente_id": (
                                    concorrente["id"]
                                ),
                                "concorrente_nome": (
                                    concorrente["nome"]
                                ),
                                "motivo": (
                                    "Nenhuma oferta verificável "
                                    "foi encontrada."
                                ),
                            }
                        )

                        continue

                    # A função de serviço adiciona ofertas novas à
                    # sessão; o commit garante a persistência.
                    sessao.commit()

                    oferta_resumida = {
                        "produto_id": resultado.produto_id,
                        "produto_nome": resultado.produto_nome,
                        "concorrente_id": (
                            resultado.concorrente_id
                        ),
                        "concorrente_nome": (
                            resultado.concorrente_nome
                        ),
                        "produto_encontrado": (
                            resultado.titulo_encontrado
                        ),
                        "preco": float(
                            resultado.preco
                        ),
                        "correspondencia": (
                            resultado.tipo_correspondencia
                        ),
                        "url": resultado.url,
                        "fonte": resultado.fonte,
                    }

                    if resultado.fonte == "cache":
                        ofertas_cache.append(
                            oferta_resumida
                        )
                    else:
                        ofertas_web.append(
                            oferta_resumida
                        )

                except Exception as erro:
                    sessao.rollback()

                    falhas.append(
                        {
                            "produto_id": produto["id"],
                            "produto_nome": produto["nome"],
                            "concorrente_id": (
                                concorrente["id"]
                            ),
                            "concorrente_nome": (
                                concorrente["nome"]
                            ),
                            "erro": str(erro),
                        }
                    )

        quantidade_combinacoes = (
            len(produtos_dados)
            * len(concorrentes_dados)
        )

        return {
            "quantidade_produtos": len(
                produtos_dados
            ),
            "quantidade_concorrentes": len(
                concorrentes_dados
            ),
            "quantidade_combinacoes": (
                quantidade_combinacoes
            ),
            "quantidade_cache": len(
                ofertas_cache
            ),
            "quantidade_web": len(
                ofertas_web
            ),
            "quantidade_nao_encontradas": len(
                nao_encontradas
            ),
            "quantidade_falhas": len(
                falhas
            ),
            "ofertas_cache": ofertas_cache,
            "ofertas_web": ofertas_web,
            "nao_encontradas": nao_encontradas,
            "falhas": falhas,
        }

def _comparar_catalogo_concorrentes(
    coletar_web: bool = True,
) -> tuple[
    str,
    dict[str, Any],
]:
    """
    Compara produtos internos somente com ofertas verificadas
    e armazenadas no banco.

    Completa primeiro as ofertas ausentes ou desatualizadas,
    reutilizando o cache sempre que possível.
    """

    if coletar_web:
            coleta = _coletar_ofertas_catalogo()
    else:
        coleta = {
            "quantidade_produtos": 0,
            "quantidade_concorrentes": 0,
            "quantidade_combinacoes": 0,
            "quantidade_cache": 0,
            "quantidade_web": 0,
            "quantidade_nao_encontradas": 0,
            "quantidade_falhas": 0,
            "ofertas_cache": [],
            "ofertas_web": [],
            "nao_encontradas": [],
            "falhas": [],
        }

    with SessionLocal() as sessao:
        produtos = listar_produtos(
            sessao=sessao,
            apenas_ativos=True,
        )

        produtos_dados = {
            produto.id: {
                "id": produto.id,
                "nome": produto.nome,
                "preco_venda": float(
                    produto.preco_venda
                ),
            }
            for produto in produtos
        }

    ofertas = _obter_ofertas_mais_recentes()

    comparacoes: list[dict[str, Any]] = []

    for oferta in ofertas:
        produto = produtos_dados.get(
            oferta["produto_id"]
        )

        if produto is None:
            continue

        preco_interno = Decimal(
            str(produto["preco_venda"])
        )

        preco_concorrente = Decimal(
            str(oferta["preco"])
        )

        diferenca = (
            preco_interno
            - preco_concorrente
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        percentual = Decimal("0")

        if preco_concorrente != 0:
            percentual = (
                diferenca
                / preco_concorrente
                * Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        comparacoes.append(
            {
                **oferta,
                "preco_interno": float(
                    preco_interno
                ),
                "diferenca_valor": float(
                    diferenca
                ),
                "diferenca_percentual": float(
                    percentual
                ),
            }
        )

    if not comparacoes:
        return (
            (
                "Ainda não há ofertas concorrentes verificadas "
                "armazenadas para comparar com nosso catálogo."
            ),
            {
                "quantidade_produtos": len(
                    produtos_dados
                ),
                "quantidade_comparacoes": 0,
                "comparacoes": [],
                "coleta": coleta,
            },
        )

    comparacoes.sort(
        key=lambda item: (
            item["produto_nome"] or "",
            item["concorrente_nome"] or "",
        )
    )

    linhas = [
        "## Comparação com concorrentes",
        "",
    ]

    produtos_com_comparacao: set[int] = set()

    for item in comparacoes:
        produtos_com_comparacao.add(
            item["produto_id"]
        )

        diferenca = Decimal(
            str(item["diferenca_valor"])
        )

        percentual = Decimal(
            str(item["diferenca_percentual"])
        )

        if diferenca > 0:
            situacao = (
                f"nosso preço está "
                f"{_formatar_brl(diferenca)} "
                f"({_formatar_percentual(percentual)}) "
                "mais alto"
            )

        elif diferenca < 0:
            situacao = (
                f"nosso preço está "
                f"{_formatar_brl(abs(diferenca))} "
                f"({_formatar_percentual(abs(percentual))}) "
                "mais baixo"
            )

        else:
            situacao = "os preços são iguais"

        linhas.extend(
            [
                f"### {item['produto_nome']}",
                (
                    f"- Nosso preço: "
                    f"{_formatar_brl(item['preco_interno'])}"
                ),
                (
                    f"- {item['concorrente_nome']}: "
                    f"{_formatar_brl(item['preco'])}"
                ),
                (
                    f"- Correspondência: "
                    f"{item['correspondencia']}"
                ),
                f"- Resultado: {situacao}.",
            ]
        )

        if item.get("url"):
            linhas.append(
                f"- URL: {item['url']}"
            )

        linhas.append("")


    if coletar_web:
        linhas.extend(
            [
                "## Resumo da coleta",
                "",
                (
                    f"- Produtos analisados: "
                    f"{coleta['quantidade_produtos']}"
                ),
                (
                    f"- Concorrentes consultados: "
                    f"{coleta['quantidade_concorrentes']}"
                ),
                (
                    f"- Combinações analisadas: "
                    f"{coleta['quantidade_combinacoes']}"
                ),
                (
                    f"- Ofertas reutilizadas do cache: "
                    f"{coleta['quantidade_cache']}"
                ),
                (
                    f"- Novas ofertas coletadas e salvas: "
                    f"{coleta['quantidade_web']}"
                ),
                (
                    f"- Combinações sem oferta verificável: "
                    f"{coleta['quantidade_nao_encontradas']}"
                ),
                (
                    f"- Falhas técnicas: "
                    f"{coleta['quantidade_falhas']}"
                ),
                "",
            ]
        )
    
    quantidade_sem_comparacao = (
        len(produtos_dados)
        - len(produtos_com_comparacao)
    )

    if quantidade_sem_comparacao > 0:
        linhas.extend(
            [
                (
                    f"**Cobertura:** "
                    f"{len(produtos_com_comparacao)} de "
                    f"{len(produtos_dados)} produtos possuem "
                    "ao menos uma oferta concorrente verificada."
                ),
                "",
                (
                    f"{quantidade_sem_comparacao} produto(s) ainda "
                    "não possuem dados concorrentes verificáveis "
                    "armazenados."
                ),
            ]
        )

    return (
        "\n".join(linhas),
        {
            "quantidade_produtos": len(
                produtos_dados
            ),
            "quantidade_produtos_com_oferta": len(
                produtos_com_comparacao
            ),
            "quantidade_comparacoes": len(
                comparacoes
            ),
            "comparacoes": comparacoes,
            "coleta": coleta,
        },
    )


def _listar_produtos_equivalentes(
    contexto: ContextoResolvido,
) -> tuple[str, dict[str, Any]]:
    """
    Lista produtos que possuem oferta exata ou equivalente
    registrada para o concorrente selecionado.
    """

    concorrente = contexto.concorrente

    assert concorrente is not None

    ofertas = _obter_ofertas_mais_recentes(
        concorrente_id=concorrente["id"],
    )

    tipos_aceitos = {
        "exato",
        "equivalente",
    }

    equivalentes = [
        oferta
        for oferta in ofertas
        if oferta["correspondencia"]
        in tipos_aceitos
    ]

    if not equivalentes:
        return (
            (
                "Não foram encontrados produtos com correspondência "
                f"exata ou equivalente na {concorrente['nome']} "
                "entre as ofertas verificadas armazenadas."
            ),
            {
                "concorrente": concorrente,
                "quantidade": 0,
                "produtos": [],
            },
        )

    equivalentes.sort(
        key=lambda item: (
            item["produto_nome"] or ""
        )
    )

    linhas = [
        (
            f"## Produtos em comum ou equivalentes com "
            f"{concorrente['nome']}"
        ),
        "",
    ]

    for item in equivalentes:
        linhas.extend(
            [
                f"### {item['produto_nome']}",
                (
                    f"- Produto encontrado: "
                    f"{item['produto_encontrado']}"
                ),
                (
                    f"- Correspondência: "
                    f"{item['correspondencia']}"
                ),
                (
                    f"- Nosso preço: "
                    f"{_formatar_brl(item['preco_interno'])}"
                ),
                (
                    f"- Preço concorrente: "
                    f"{_formatar_brl(item['preco'])}"
                ),
            ]
        )

        if item.get("url"):
            linhas.append(
                f"- URL: {item['url']}"
            )

        linhas.append("")

    return (
        "\n".join(linhas),
        {
            "concorrente": concorrente,
            "quantidade": len(
                equivalentes
            ),
            "produtos": equivalentes,
        },
    )

def _filtrar_comparacoes_catalogo(
    pergunta: str,
) -> tuple[
    str,
    dict[str, Any],
]:
    """
    Filtra as comparações verificadas do catálogo.

    “Mais baratos” significa que o preço da nossa loja é menor
    que o preço concorrente.

    “Mais caros” significa que o preço da nossa loja é maior
    que o preço concorrente.
    """

    texto = normalizar_texto(
        pergunta
    )

    _, dados_catalogo = (
        _comparar_catalogo_concorrentes(
            coletar_web=False
        )
    )

    comparacoes = list(
        dados_catalogo.get(
            "comparacoes",
            [],
        )
    )

    mostrar_mais_baratos = _contem_algum(
        texto,
        _TERMOS_NOS_MAIS_BARATOS,
    )

    mostrar_mais_caros = _contem_algum(
        texto,
        _TERMOS_NOS_MAIS_CAROS,
    )

    if mostrar_mais_baratos:
        modo = "mais_baratos"

        selecionadas = [
            item
            for item in comparacoes
            if Decimal(
                str(
                    item["diferenca_valor"]
                )
            ) < 0
        ]

        titulo = (
            "## Produtos em que nossa loja "
            "está mais barata"
        )

        mensagem_vazia = (
            "Não foram encontrados produtos em que "
            "nosso preço esteja abaixo do concorrente "
            "entre as ofertas verificadas."
        )

    elif mostrar_mais_caros:
        modo = "mais_caros"

        selecionadas = [
            item
            for item in comparacoes
            if Decimal(
                str(
                    item["diferenca_valor"]
                )
            ) > 0
        ]

        titulo = (
            "## Produtos em que nossa loja "
            "está mais cara"
        )

        mensagem_vazia = (
            "Não foram encontrados produtos em que "
            "nosso preço esteja acima do concorrente "
            "entre as ofertas verificadas."
        )

    else:
        return (
            (
                "Informe se deseja ver os produtos em que "
                "nossa loja está mais barata ou mais cara."
            ),
            {
                "modo": None,
                "quantidade": 0,
                "comparacoes": [],
            },
        )

    if not selecionadas:
        return (
            mensagem_vazia,
            {
                "modo": modo,
                "quantidade": 0,
                "comparacoes": [],
            },
        )

    selecionadas.sort(
        key=lambda item: abs(
            Decimal(
                str(
                    item["diferenca_valor"]
                )
            )
        ),
        reverse=True,
    )

    linhas = [
        titulo,
        "",
    ]

    for item in selecionadas:
        diferenca = abs(
            Decimal(
                str(
                    item["diferenca_valor"]
                )
            )
        )

        percentual = abs(
            Decimal(
                str(
                    item["diferenca_percentual"]
                )
            )
        )

        linhas.extend(
            [
                f"### {item['produto_nome']}",
                (
                    f"- Nosso preço: "
                    f"{_formatar_brl(item['preco_interno'])}"
                ),
                (
                    f"- {item['concorrente_nome']}: "
                    f"{_formatar_brl(item['preco'])}"
                ),
                (
                    f"- Diferença: "
                    f"{_formatar_brl(diferenca)} "
                    f"({_formatar_percentual(percentual)})"
                ),
            ]
        )

        if item.get("url"):
            linhas.append(
                f"- URL: {item['url']}"
            )

        linhas.append("")

    return (
        "\n".join(linhas),
        {
            "modo": modo,
            "quantidade": len(
                selecionadas
            ),
            "comparacoes": selecionadas,
        },
    )



def _avaliar_reducao_preco(
    memoria: Mapping[str, Any],
    contexto: ContextoResolvido | None = None,
    margem_minima_percentual: Decimal = Decimal("10"),
) -> tuple[str, dict[str, Any]]:
    """
    Avalia se vale a pena reduzir o preço do último produto comparado.

    Usa somente:
    - última comparação concorrencial confirmada;
    - custo histórico registrado no banco;
    - análise determinística de margem.
    """

    comparacao = memoria.get(
        "ultima_comparacao"
    )
    
    # Se não existe uma comparação anterior, tenta montar uma
# automaticamente usando o produto informado na pergunta
# e a melhor oferta concorrente já armazenada no banco.
    if (
        not isinstance(comparacao, Mapping)
        and contexto is not None
        and contexto.produto is not None
    ):
        produto = contexto.produto

        with SessionLocal() as sessao:
            menor_preco = buscar_menor_preco_concorrente(
                sessao=sessao,
                produto_id=produto["id"],
                apenas_correspondencia_exata=True,
            )

            if menor_preco is not None:
                concorrente = menor_preco.concorrente

                preco_interno = Decimal(
                    str(produto["preco_venda"])
                )

                preco_concorrente = Decimal(
                    str(menor_preco.preco)
                )

                diferenca = (
                    preco_interno
                    - preco_concorrente
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )

                percentual = (
                    diferenca
                    / preco_concorrente
                    * Decimal("100")
                    if preco_concorrente != 0
                    else Decimal("0")
                )

                comparacao = {
                    "produto_id": produto["id"],
                    "produto_nome": produto["nome"],
                    "concorrente_id": menor_preco.concorrente_id,
                    "concorrente_nome": concorrente.nome,
                    "preco_interno": float(
                        preco_interno
                    ),
                    "preco_concorrente": float(
                        preco_concorrente
                    ),
                    "diferenca_valor": float(
                        diferenca
                    ),
                    "diferenca_percentual": float(
                        percentual
                    ),
                    "url": menor_preco.url,
                    "coletado_em": (
                        menor_preco.coletado_em.isoformat()
                        if menor_preco.coletado_em
                        else None
                    ),
                }

    if not isinstance(comparacao, Mapping):
        return (
            (
                "Não existe uma comparação concorrencial confirmada "
                "para avaliar uma redução de preço."
            ),
            {
                "avaliacao_disponivel": False,
                "motivo": "comparacao_ausente",
            },
        )

    produto_id = comparacao.get(
        "produto_id"
    )

    produto_nome = comparacao.get(
        "produto_nome"
    )

    concorrente_nome = comparacao.get(
        "concorrente_nome"
    )

    preco_interno = Decimal(
        str(
            comparacao.get(
                "preco_interno"
            )
        )
    )

    preco_concorrente = Decimal(
        str(
            comparacao.get(
                "preco_concorrente"
            )
        )
    )

    if (
        not isinstance(produto_id, int)
        or produto_id <= 0
    ):
        return (
            "A última comparação não possui um produto válido.",
            {
                "avaliacao_disponivel": False,
                "motivo": "produto_invalido",
            },
        )

    diferenca = (
        preco_interno
        - preco_concorrente
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    # Nossa loja já está igual ou abaixo do concorrente.
    if diferenca <= 0:
        resposta = (
            f"**{produto_nome}**\n\n"
            "Não é necessário reduzir o preço para acompanhar "
            f"a {concorrente_nome}.\n\n"
            f"- Nosso preço: {_formatar_brl(preco_interno)}\n"
            f"- {concorrente_nome}: "
            f"{_formatar_brl(preco_concorrente)}\n"
        )

        if diferenca < 0:
            resposta += (
                "- Nosso preço já está "
                f"{_formatar_brl(abs(diferenca))} abaixo."
            )
        else:
            resposta += "- Os preços já são iguais."

        return (
            resposta,
            {
                "avaliacao_disponivel": True,
                "produto_id": produto_id,
                "produto_nome": produto_nome,
                "preco_interno": float(
                    preco_interno
                ),
                "preco_concorrente": float(
                    preco_concorrente
                ),
                "reducao_recomendada": False,
                "motivo": (
                    "preco_interno_igual_ou_menor"
                ),
            },
        )

    desconto_necessario = (
        diferenca
        / preco_interno
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    with SessionLocal() as sessao:
        analise = analisar_margem_produto(
            sessao=sessao,
            produto_id=produto_id,
            desconto_percentual=float(
                desconto_necessario
            ),
            margem_minima_percentual=float(
                margem_minima_percentual
            ),
        )

    if not analise.get(
        "possui_custo_referencia",
        False,
    ):
        return (
            (
                f"**{produto_nome}**\n\n"
                "Não é possível recomendar uma redução de preço "
                "com segurança porque não existe custo de referência "
                "confirmado para esse produto."
            ),
            {
                "avaliacao_disponivel": False,
                "produto_id": produto_id,
                "produto_nome": produto_nome,
                "motivo": "custo_indisponivel",
                "comparacao": dict(
                    comparacao
                ),
            },
        )

    atende_margem = (
        analise.get(
            "atende_margem_minima"
        )
        is True
    )

    preco_com_desconto = Decimal(
        str(
            analise.get(
                "preco_com_desconto"
            )
        )
    )

    margem_resultante = Decimal(
        str(
            analise.get(
                "margem_com_desconto_percentual"
            )
        )
    )

    desconto_maximo_margem = Decimal(
        str(
            analise.get(
                "desconto_maximo_com_margem_exigida_percentual"
            )
        )
    )

    preco_minimo_margem = Decimal(
        str(
            analise.get(
                "preco_minimo_com_margem_exigida"
            )
        )
    )

    linhas = [
        f"**{produto_nome}**",
        "",
        "## Avaliação de redução de preço",
        "",
        (
            f"- Nosso preço: "
            f"{_formatar_brl(preco_interno)}"
        ),
        (
            f"- Preço da {concorrente_nome}: "
            f"{_formatar_brl(preco_concorrente)}"
        ),
        (
            f"- Desconto necessário para igualar: "
            f"{_formatar_percentual(desconto_necessario)}"
        ),
        (
            f"- Preço após o desconto: "
            f"{_formatar_brl(preco_com_desconto)}"
        ),
        (
            f"- Margem resultante: "
            f"{_formatar_percentual(margem_resultante)}"
        ),
        (
            f"- Margem mínima definida: "
            f"{_formatar_percentual(margem_minima_percentual)}"
        ),
        "",
    ]

    if atende_margem:
        linhas.extend(
            [
                (
                    "**Recomendação:** financeiramente, é possível "
                    "igualar o preço do concorrente mantendo a margem "
                    "mínima definida."
                ),
                (
                    "A decisão final ainda deve considerar demanda, "
                    "posicionamento e estratégia comercial."
                ),
            ]
        )

        recomendacao = (
            "pode_igualar_mantendo_margem"
        )

    else:
        diferenca_preco_seguro = (
            preco_minimo_margem
            - preco_concorrente
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        linhas.extend(
            [
                (
                    "**Recomendação:** não é recomendável igualar "
                    "o preço do concorrente mantendo a política atual "
                    "de margem."
                ),
                (
                    f"O desconto máximo preservando "
                    f"{_formatar_percentual(margem_minima_percentual)} "
                    f"de margem é "
                    f"{_formatar_percentual(desconto_maximo_margem)}, "
                    f"resultando em um preço mínimo de "
                    f"{_formatar_brl_markdown(preco_minimo_margem)}."
                ),
            ]
        )

        if diferenca_preco_seguro > 0:
            linhas.append(
                (
                    "Mesmo nesse preço mínimo seguro, nossa oferta "
                    f"ficaria {_formatar_brl_markdown(diferenca_preco_seguro)} "
                    f"acima da {concorrente_nome}."
                )
            )

        recomendacao = (
            "nao_igualar_margem_insuficiente"
        )

    linhas.extend(
        [
            "",
            (
                "**Limitação:** o custo usado é histórico e deve ser "
                "confirmado antes de alterar o preço."
            ),
        ]
    )

    dados = {
        "avaliacao_disponivel": True,
        "produto_id": produto_id,
        "produto_nome": produto_nome,
        "concorrente_nome": concorrente_nome,
        "preco_interno": float(
            preco_interno
        ),
        "preco_concorrente": float(
            preco_concorrente
        ),
        "diferenca_valor": float(
            diferenca
        ),
        "desconto_necessario_percentual": float(
            desconto_necessario
        ),
        "preco_com_desconto": float(
            preco_com_desconto
        ),
        "margem_resultante_percentual": float(
            margem_resultante
        ),
        "margem_minima_percentual": float(
            margem_minima_percentual
        ),
        "atende_margem_minima": atende_margem,
        "desconto_maximo_seguro_percentual": float(
            desconto_maximo_margem
        ),
        "preco_minimo_com_margem": float(
            preco_minimo_margem
        ),
        "recomendacao": recomendacao,
        "comparacao": dict(
            comparacao
        ),
        "analise_margem": analise,
    }

    return (
        "\n".join(
            linhas
        ),
        dados,
    )


def executar_fluxo_deterministico(
    pergunta: str,
    memoria: Mapping[str, Any] | None = None,
) -> ResultadoOrquestracao:
    """
    Resolve o contexto e executa um fluxo conhecido.

    Quando nenhum fluxo determinístico for reconhecido, retorna
    tratado=False para permitir o fallback ao agente tradicional.
    """

    memoria_atual = normalizar_memoria(
        memoria
    )

    contexto = resolver_contexto(
        pergunta=pergunta,
        memoria=memoria_atual,
    )

    fluxo = detectar_fluxo(
        pergunta=pergunta,
        contexto=contexto,
        memoria=memoria_atual,
    )

    if fluxo is None:
        return ResultadoOrquestracao(
            tratado=False,
            resposta=None,
            memoria=memoria_atual,
        )

    if contexto.ambiguidades:
        return ResultadoOrquestracao(
            tratado=True,
            resposta=(
                "Não foi possível identificar uma única "
                "entidade.\n\n"
                + "\n".join(
                    f"- {item}"
                    for item
                    in contexto.ambiguidades
                )
            ),
            memoria=memoria_atual,
            fluxo=fluxo,
        )


    if fluxo == "avaliar_reducao_preco":
        resposta, dados = _avaliar_reducao_preco(
            memoria=memoria_atual,
            contexto=contexto,
        )

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao="analisar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )

    if fluxo == "listar_produtos":
        resposta, dados = _listar_produtos()

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo="listar_produtos",
            intencao="consultar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )
        
    if fluxo == "consultar_preco_interno":
        if contexto.produto is None:
            return ResultadoOrquestracao(
                tratado=True,
                resposta=(
                    "Não foi possível identificar o produto. "
                    "Informe o nome e o armazenamento."
                ),
                memoria=memoria_atual,
                fluxo=fluxo,
            )

        memoria_atual = registrar_produto(
            memoria_atual,
            contexto.produto,
        )

        resposta, dados = _consultar_preco_interno(
            contexto
        )

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao="consultar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )
        
    if fluxo == "comparar_catalogo_concorrentes":
        resposta, dados = (
            _comparar_catalogo_concorrentes()
        )

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao="comparar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )
        
    if fluxo == "filtrar_comparacoes_catalogo":
        resposta, dados = (
            _filtrar_comparacoes_catalogo(
                pergunta
            )
        )

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao="comparar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )


    if fluxo == "listar_produtos_equivalentes":
        if contexto.concorrente is None:
            return ResultadoOrquestracao(
                tratado=True,
                resposta=(
                    "Não foi possível identificar o concorrente."
                ),
                memoria=memoria_atual,
                fluxo=fluxo,
            )

        memoria_atual = registrar_concorrente(
            memoria_atual,
            contexto.concorrente,
        )

        resposta, dados = (
            _listar_produtos_equivalentes(
                contexto
            )
        )

        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao="consultar",
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=resposta,
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=dados,
        )

    if contexto.produto is None:
        return ResultadoOrquestracao(
            tratado=True,
            resposta=(
                "Não foi possível identificar o produto. "
                "Informe o nome e, quando necessário, "
                "o armazenamento."
            ),
            memoria=memoria_atual,
            fluxo=fluxo,
        )

    if contexto.concorrente is None:
        return ResultadoOrquestracao(
            tratado=True,
            resposta=(
                "Não foi possível identificar o concorrente. "
                "Informe a loja que deseja consultar."
            ),
            memoria=memoria_atual,
            fluxo=fluxo,
        )

    memoria_atual = registrar_produto(
        memoria_atual,
        contexto.produto,
    )

    memoria_atual = registrar_concorrente(
        memoria_atual,
        contexto.concorrente,
    )

    texto = normalizar_texto(
        pergunta
    )

    forcar_atualizacao = _contem_algum(
        texto,
        _TERMOS_ATUALIZACAO,
    )

    oferta = _consultar_oferta(
        contexto=contexto,
        forcar_atualizacao=forcar_atualizacao,
    )

    if oferta is None:
        memoria_atual = registrar_fluxo(
            memoria_atual,
            fluxo=fluxo,
            intencao=(
                "comparar"
                if fluxo
                == "comparar_preco_concorrente"
                else "consultar"
            ),
        )

        return ResultadoOrquestracao(
            tratado=True,
            resposta=(
                "Não foi encontrada uma oferta concorrente "
                "verificável para esse produto."
            ),
            memoria=memoria_atual,
            fluxo=fluxo,
        )

    memoria_atual = registrar_oferta(
        memoria_atual,
        oferta,
    )

    if fluxo == "consultar_preco_concorrente":
        return ResultadoOrquestracao(
            tratado=True,
            resposta=_resposta_oferta(
                oferta
            ),
            memoria=memoria_atual,
            fluxo=fluxo,
            dados=oferta,
        )

    resposta, comparacao = _comparar_precos(
        contexto=contexto,
        oferta=oferta,
    )

    memoria_atual = registrar_comparacao(
        memoria_atual,
        comparacao,
    )

    return ResultadoOrquestracao(
        tratado=True,
        resposta=resposta,
        memoria=memoria_atual,
        fluxo=fluxo,
        dados=comparacao,
    )


__all__ = [
    "ResultadoOrquestracao",
    "detectar_fluxo",
    "executar_fluxo_deterministico",
    "normalizar_texto",
]