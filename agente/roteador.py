"""
Roteamento seletivo de ferramentas do Secretário IA Empresarial.

Estratégia:

1. Regras determinísticas para fluxos críticos e inequívocos.
2. Detecção de conceitos empresariais, em vez de frases completas.
3. Seleção genérica por relevância quando não houver regra crítica.
4. Classificador LLM econômico somente quando o resultado for fraco.

O roteador não consulta banco, web ou modelo de linguagem.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

from langchain_core.tools import BaseTool

from agente.ferramentas.analises import (
    FERRAMENTAS_ANALISES,
)
from agente.ferramentas.campanha import (
    FERRAMENTAS_CAMPANHA,
)
from agente.ferramentas.compra import (
    FERRAMENTAS_COMPRA,
)
from agente.ferramentas.concorrente import (
    FERRAMENTAS_CONCORRENTE,
)
from agente.ferramentas.estoque import (
    FERRAMENTAS_ESTOQUE,
)
from agente.ferramentas.fornecedor import (
    FERRAMENTAS_FORNECEDOR,
)
from agente.ferramentas.preco_concorrente import (
    FERRAMENTAS_PRECO_CONCORRENTE,
)
from agente.ferramentas.produto import (
    FERRAMENTAS_PRODUTO,
)
from agente.ferramentas.venda import (
    FERRAMENTAS_VENDA,
)


LIMITE_FERRAMENTAS_POR_REQUISICAO = 8


@dataclass(frozen=True)
class ResultadoRoteamento:
    """
    Resultado completo produzido pelo roteador.
    """

    intencao: str
    categorias: tuple[str, ...]
    ferramentas: tuple[BaseTool, ...]
    motivo: str

    @property
    def nomes_ferramentas(self) -> list[str]:
        return [
            ferramenta.name
            for ferramenta in self.ferramentas
        ]


# ============================================================
# REGISTRO DE FERRAMENTAS
# ============================================================

GRUPOS_FERRAMENTAS: dict[
    str,
    Sequence[BaseTool],
] = {
    "analises": FERRAMENTAS_ANALISES,
    "produto": FERRAMENTAS_PRODUTO,
    "estoque": FERRAMENTAS_ESTOQUE,
    "fornecedor": FERRAMENTAS_FORNECEDOR,
    "compra": FERRAMENTAS_COMPRA,
    "venda": FERRAMENTAS_VENDA,
    "campanha": FERRAMENTAS_CAMPANHA,
    "concorrente": FERRAMENTAS_CONCORRENTE,
    "preco_concorrente": (
        FERRAMENTAS_PRECO_CONCORRENTE
    ),
}


# ============================================================
# CONCEITOS EMPRESARIAIS
# ============================================================

CONCEITOS: dict[str, set[str]] = {
    "produto": {
        "produto",
        "produtos",
        "item",
        "itens",
        "catalogo",
        "smartphone",
        "smartphones",
        "celular",
        "celulares",
        "aparelho",
        "aparelhos",
        "modelo",
        "modelos",
        "iphone",
        "galaxy",
        "motorola",
        "xiaomi",
        "redmi",
        "asus",
    },
    "estoque": {
        "estoque",
        "estoques",
        "quantidade disponivel",
        "saldo",
        "unidades disponiveis",
        "estoque minimo",
        "estoque baixo",
        "estoque critico",
        "sem estoque",
        "em falta",
        "ruptura",
        "cobertura",
        "dias de cobertura",
    },
    "fornecedor": {
        "fornecedor",
        "fornecedores",
        "distribuidor",
        "distribuidores",
        "parceiro comercial",
        "parceiros comerciais",
        "quem fornece",
        "quem entrega",
        "prazo de entrega",
    },
    "compra": {
        "compra",
        "compras",
        "comprar",
        "pedido",
        "pedidos",
        "pedido de compra",
        "adquirir",
        "aquisicao",
        "repor",
        "reposicao",
        "reabastecer",
    },
    "venda": {
        "venda",
        "vendas",
        "vender",
        "vendido",
        "vendidos",
        "demanda",
        "faturamento",
        "receita",
        "mais vendido",
        "mais vendidos",
    },
    "campanha": {
        "campanha",
        "campanhas",
        "marketing",
        "publicidade",
        "promocao",
        "promocoes",
    },
    "concorrente": {
        "concorrente",
        "concorrentes",
        "concorrencia",
        "loja concorrente",
        "amazon",
        "amazon brasil",
        "magalu",
        "magazine luiza",
    },
    "preco_concorrente": {
        "preco concorrente",
        "precos concorrentes",
        "preco da concorrencia",
        "comparar preco",
        "comparacao de preco",
        "oferta concorrente",
        "menor preco concorrente",
    },
}


TERMOS_PRECO = {
    "preco",
    "precos",
    "valor",
    "valores",
    "oferta",
    "ofertas",
    "custa",
    "custando",
    "quanto custa",
    "quanto esta",
}


TERMOS_ANALISE = {
    "analise",
    "analisar",
    "avaliar",
    "diagnostico",
    "situacao",
    "visao geral",
    "painel",
    "alerta",
    "alertas",
    "risco",
    "riscos",
    "prioridade",
    "prioridades",
    "problema",
    "problemas",
    "margem",
    "lucro",
    "rentabilidade",
    "desconto",
    "reposicao",
    "ruptura",
    "cobertura",
    "recomendacao",
    "recomendar",
    "melhor",
    "mais adequado",
    "vale a pena",
}


TERMOS_EMPRESA_GERAL = {
    "empresa",
    "negocio",
    "operacao",
    "operacoes",
    "gestao",
    "saude da empresa",
    "desempenho da empresa",
    "principais riscos",
    "prioridades da empresa",
}


TERMOS_DECISAO = {
    "melhor",
    "recomendar",
    "recomenda",
    "recomendaria",
    "indicacao",
    "indicar",
    "escolher",
    "escolha",
    "preferir",
    "mais adequado",
    "mais vantajoso",
    "vale a pena",
    "devemos",
    "deveria",
    "priorizar",
    "prioridade",
}


TERMOS_REPOSICAO = {
    "comprar",
    "compra",
    "compre",
    "adquirir",
    "aquisicao",
    "repor",
    "reposicao",
    "reabastecer",
    "abastecer",
    "novo pedido",
    "proximo pedido",
    "fazer pedido",
    "realizar pedido",
    "comprar primeiro",
    "repor primeiro",
}


TERMOS_URGENCIA_ESTOQUE = {
    "estoque critico",
    "estoque baixo",
    "baixo estoque",
    "sem estoque",
    "em falta",
    "falta de estoque",
    "risco de ruptura",
    "ruptura",
    "acabando",
    "poucas unidades",
    "cobertura baixa",
    "demanda alta",
    "muitas vendas",
    "vendas recentes",
}


TERMOS_COMPARACAO_FORNECEDOR = {
    "custo e prazo",
    "preco e prazo",
    "melhor custo",
    "menor custo",
    "melhor preco",
    "menor preco",
    "melhor prazo",
    "entrega mais rapida",
    "quem entrega mais rapido",
    "melhor combinacao",
}


TERMOS_ESCOPO_GLOBAL = {
    "qual produto",
    "quais produtos",
    "qual item",
    "quais itens",
    "entre os produtos",
    "entre todos",
    "todos os produtos",
    "todo o catalogo",
    "maior risco",
    "menor cobertura",
    "prioridade maxima",
    "maior prioridade",
    "comprar primeiro",
    "repor primeiro",
    "atencao imediata",
    "mais urgente",
}


TERMOS_PRIORIDADE_REPOSICAO = {
    "prioridade de reposicao",
    "prioridade para reposicao",
    "prioridade maxima de reposicao",
    "deveria receber prioridade",
    "devemos priorizar",
    "merece prioridade",
    "comprar primeiro",
    "repor primeiro",
    "maior risco de ruptura",
    "maior necessidade de reposicao",
    "qual acao devemos tomar",
}


TERMOS_ESCRITA = {
    "cadastre",
    "cadastrar",
    "registre",
    "registrar",
    "crie",
    "criar",
    "adicione",
    "adicionar",
    "atualize",
    "atualizar",
    "altere",
    "alterar",
    "modifique",
    "modificar",
    "exclua",
    "excluir",
    "remova",
    "remover",
    "desative",
    "desativar",
    "reative",
    "reativar",
    "cancele",
    "cancelar",
}


PREFIXOS_LEITURA = (
    "buscar",
    "consultar",
    "listar",
    "obter",
    "localizar",
    "pesquisar",
    "verificar",
    "analisar",
    "calcular",
    "recomendar",
    "gerar",
)


PREFIXOS_ESCRITA = (
    "criar",
    "cadastrar",
    "registrar",
    "adicionar",
    "modificar",
    "atualizar",
    "alterar",
    "definir",
    "remover",
    "desativar",
    "reativar",
    "marcar",
    "associar",
)


# ============================================================
# CONJUNTOS MÍNIMOS PARA FLUXOS CRÍTICOS
# ============================================================

FERRAMENTAS_PRECO_CONCORRENTE = {
    "pesquisar_smartphones",
    "consultar_concorrentes",
    "buscar_preco_atual_concorrente",
}


FERRAMENTAS_RECOMENDACAO_FORNECEDOR = {
    "pesquisar_smartphones",
    "analisar_risco_estoque_produto",
    "recomendar_fornecedor_para_reposicao",
}


FERRAMENTAS_PRIORIDADE_REPOSICAO = {
    "analisar_prioridades_reposicao_catalogo",
}


FERRAMENTAS_POR_INTENCAO_CLASSIFICADA: dict[
    str,
    set[str],
] = {
    "recomendacao_fornecedor": {
        "pesquisar_smartphones",
        "analisar_risco_estoque_produto",
        "recomendar_fornecedor_para_reposicao",
    },
    "risco_estoque": {
        "analisar_prioridades_reposicao_catalogo",
        "analisar_risco_estoque_produto",
        "consultar_alertas_estoque",
    },
    "consulta_estoque": {
        "pesquisar_smartphones",
        "consultar_estoque_produto",
        "consultar_estoques",
        "consultar_produtos_com_estoque_baixo",
    },
    "analise_vendas": {
        "pesquisar_smartphones",
        "consultar_vendas",
        "consultar_vendas_produto",
        "consultar_produtos_mais_vendidos",
    },
    "consulta_compras": {
        "pesquisar_smartphones",
        "consultar_compras",
        "consultar_compras_produto",
        "consultar_compras_em_aberto",
    },
    "analise_margem": {
        "pesquisar_smartphones",
        "analisar_desconto_produto",
        "analisar_descontos_todos_produtos",
    },
    "analise_empresa": {
        "consultar_painel_alertas_empresariais",
    },
    "consulta_produto": {
        "pesquisar_smartphones",
        "consultar_produtos",
        "consultar_produto_por_id",
    },
    "consulta_fornecedor": {
        "consultar_fornecedores",
        "pesquisar_fornecedores_cadastrados",
        "consultar_fornecedor_por_id",
    },
    "consulta_concorrente": {
        "consultar_concorrentes",
        "consultar_ofertas_concorrentes",
    },
    "conversa": set(),
    "esclarecimento": set(),
}


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def normalizar_texto(
    texto: str,
) -> str:
    """
    Converte texto para minúsculas, remove acentos e compacta espaços.
    """

    texto_sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFKD",
            texto,
        )
        if not unicodedata.combining(
            caractere
        )
    )

    return " ".join(
        texto_sem_acentos
        .lower()
        .split()
    )


def _contem_algum(
    texto: str,
    termos: Iterable[str],
) -> bool:
    return any(
        termo in texto
        for termo in termos
    )


def _contar_termos(
    texto: str,
    termos: Iterable[str],
) -> int:
    return sum(
        1
        for termo in termos
        if termo in texto
    )


def _remover_duplicadas(
    ferramentas: Iterable[BaseTool],
) -> list[BaseTool]:
    resultado: list[BaseTool] = []
    nomes: set[str] = set()

    for ferramenta in ferramentas:
        if ferramenta.name in nomes:
            continue

        nomes.add(
            ferramenta.name
        )

        resultado.append(
            ferramenta
        )

    return resultado


def _todas_ferramentas() -> list[BaseTool]:
    return _remover_duplicadas(
        ferramenta
        for grupo in GRUPOS_FERRAMENTAS.values()
        for ferramenta in grupo
    )


def _selecionar_ferramentas_por_nome(
    nomes: set[str],
) -> list[BaseTool]:
    ferramentas = [
        ferramenta
        for ferramenta in _todas_ferramentas()
        if ferramenta.name in nomes
    ]

    nomes_encontrados = {
        ferramenta.name
        for ferramenta in ferramentas
    }

    nomes_ausentes = nomes - nomes_encontrados

    if nomes_ausentes:
        raise RuntimeError(
            "Ferramentas obrigatórias não encontradas: "
            + ", ".join(
                sorted(
                    nomes_ausentes
                )
            )
        )

    return ferramentas


# ============================================================
# DETECÇÃO DE ESCOPO E INTENÇÃO
# ============================================================

def _detectar_categorias(
    texto: str,
) -> list[str]:
    pontuacoes = {
        categoria: _contar_termos(
            texto,
            termos,
        )
        for categoria, termos
        in CONCEITOS.items()
    }

    categorias = [
        categoria
        for categoria, pontuacao
        in pontuacoes.items()
        if pontuacao > 0
    ]

    categorias.sort(
        key=lambda categoria: (
            pontuacoes[categoria]
        ),
        reverse=True,
    )

    return categorias


def _detectar_intencao(
    texto: str,
) -> str:
    if _contem_algum(
        texto,
        TERMOS_ESCRITA,
    ):
        return "escrita"

    if (
        _contem_algum(
            texto,
            TERMOS_ANALISE,
        )
        or _contem_algum(
            texto,
            TERMOS_EMPRESA_GERAL,
        )
    ):
        return "analise"

    if _detectar_categorias(
        texto
    ):
        return "leitura"

    return "conversa"


def _eh_escopo_global(
    texto: str,
) -> bool:
    return _contem_algum(
        texto,
        TERMOS_ESCOPO_GLOBAL,
    )


def _possui_produto_especifico(
    texto: str,
) -> bool:
    """
    Detecta indícios de produto individual na pergunta.

    Não precisa reconhecer todos os nomes; serve apenas para distinguir
    análise individual de consulta global.
    """

    padroes = (
        r"\biphone\b",
        r"\bgalaxy\b",
        r"\bmoto(?:rola)?\b",
        r"\bxiaomi\b",
        r"\bredmi\b",
        r"\basus\b",
        r"\bproduto\s+\d+\b",
        r"\bproduto\s+[a-z0-9]",
        r"\besse produto\b",
        r"\bdesse produto\b",
        r"\besse aparelho\b",
        r"\bdesse aparelho\b",
    )

    return any(
        re.search(
            padrao,
            texto,
        )
        for padrao in padroes
    )


# ============================================================
# REGRAS CRÍTICAS DE ALTO NÍVEL
# ============================================================

def _eh_consulta_preco_concorrente(
    texto: str,
) -> bool:
    return (
        _contem_algum(
            texto,
            TERMOS_PRECO,
        )
        and _contem_algum(
            texto,
            CONCEITOS["concorrente"],
        )
    )


def _eh_prioridade_reposicao_catalogo(
    texto: str,
) -> bool:
    """
    Detecta decisões globais de reposição.

    Exemplos:
    - Qual produto apresenta maior risco de ruptura?
    - Qual produto devemos comprar primeiro?
    - Qual merece prioridade máxima de reposição?
    """

    escopo_global = _eh_escopo_global(
        texto
    )

    contexto_reposicao = (
        _contem_algum(
            texto,
            TERMOS_PRIORIDADE_REPOSICAO,
        )
        or _contem_algum(
            texto,
            TERMOS_REPOSICAO,
        )
        or _contem_algum(
            texto,
            TERMOS_URGENCIA_ESTOQUE,
        )
    )

    menciona_multiplas_dimensoes = (
        _contar_termos(
            texto,
            {
                "estoque",
                "vendas",
                "demanda",
                "compras pendentes",
                "fornecedores",
                "prazo",
            },
        )
        >= 2
    )

    return (
        (
            escopo_global
            and contexto_reposicao
        )
        or (
            escopo_global
            and menciona_multiplas_dimensoes
        )
    )


def _eh_recomendacao_fornecedor(
    texto: str,
) -> bool:
    """
    Detecta decisão de fornecedor para um produto específico.
    """

    if _eh_prioridade_reposicao_catalogo(
        texto
    ):
        return False

    menciona_fornecedor = _contem_algum(
        texto,
        CONCEITOS["fornecedor"],
    )

    menciona_reposicao = _contem_algum(
        texto,
        TERMOS_REPOSICAO,
    )

    menciona_decisao = _contem_algum(
        texto,
        TERMOS_DECISAO,
    )

    menciona_estoque = _contem_algum(
        texto,
        TERMOS_URGENCIA_ESTOQUE,
    )

    menciona_comparacao = _contem_algum(
        texto,
        TERMOS_COMPARACAO_FORNECEDOR,
    )

    return (
        (
            menciona_fornecedor
            and (
                menciona_reposicao
                or menciona_decisao
                or menciona_estoque
                or menciona_comparacao
            )
        )
        or (
            menciona_reposicao
            and menciona_decisao
            and _possui_produto_especifico(
                texto
            )
        )
        or (
            menciona_comparacao
            and (
                menciona_fornecedor
                or _possui_produto_especifico(
                    texto
                )
            )
        )
    )


def _rotear_regra_alto_nivel(
    texto: str,
) -> ResultadoRoteamento | None:
    """
    Aplica regras inequívocas antes do roteamento genérico.
    """

    if _eh_consulta_preco_concorrente(
        texto
    ):
        ferramentas = (
            _selecionar_ferramentas_por_nome(
                FERRAMENTAS_PRECO_CONCORRENTE
            )
        )

        return ResultadoRoteamento(
            intencao="leitura",
            categorias=(
                "produto",
                "concorrente",
                "preco_concorrente",
            ),
            ferramentas=tuple(
                ferramentas
            ),
            motivo=(
                "Regra de alto nível para consulta "
                "de preço em concorrente."
            ),
        )

    if _eh_prioridade_reposicao_catalogo(
        texto
    ):
        ferramentas = (
            _selecionar_ferramentas_por_nome(
                FERRAMENTAS_PRIORIDADE_REPOSICAO
            )
        )

        return ResultadoRoteamento(
            intencao="analise",
            categorias=(
                "produto",
                "estoque",
                "venda",
                "compra",
                "fornecedor",
                "analises",
            ),
            ferramentas=tuple(
                ferramentas
            ),
            motivo=(
                "Regra de alto nível para análise global "
                "de prioridade de reposição."
            ),
        )

    if _eh_recomendacao_fornecedor(
        texto
    ):
        ferramentas = (
            _selecionar_ferramentas_por_nome(
                FERRAMENTAS_RECOMENDACAO_FORNECEDOR
            )
        )

        return ResultadoRoteamento(
            intencao="analise",
            categorias=(
                "produto",
                "estoque",
                "fornecedor",
                "compra",
                "analises",
            ),
            ferramentas=tuple(
                ferramentas
            ),
            motivo=(
                "Regra de alto nível para recomendação "
                "de fornecedor de um produto."
            ),
        )

    return None


# ============================================================
# ROTEAMENTO GENÉRICO POR RELEVÂNCIA
# ============================================================

def _eh_ferramenta_leitura(
    ferramenta: BaseTool,
) -> bool:
    nome = ferramenta.name.casefold()

    return nome.startswith(
        PREFIXOS_LEITURA
    )


def _eh_ferramenta_escrita(
    ferramenta: BaseTool,
) -> bool:
    nome = ferramenta.name.casefold()

    return nome.startswith(
        PREFIXOS_ESCRITA
    )


def _expandir_dependencias(
    categorias: list[str],
) -> list[str]:
    resultado = list(
        categorias
    )

    dependencias: dict[str, tuple[str, ...]] = {
        "venda": (
            "produto",
            "estoque",
        ),
        "compra": (
            "produto",
            "fornecedor",
            "estoque",
        ),
        "campanha": (
            "produto",
        ),
        "preco_concorrente": (
            "produto",
            "concorrente",
        ),
    }

    for categoria in categorias:
        resultado.extend(
            dependencias.get(
                categoria,
                (),
            )
        )

    return list(
        dict.fromkeys(
            resultado
        )
    )


def _ferramentas_candidatas(
    categorias: list[str],
    intencao: str,
) -> list[BaseTool]:
    candidatas: list[BaseTool] = []

    for categoria in categorias:
        candidatas.extend(
            GRUPOS_FERRAMENTAS.get(
                categoria,
                (),
            )
        )

    if intencao == "analise":
        candidatas.extend(
            FERRAMENTAS_ANALISES
        )

    return _remover_duplicadas(
        candidatas
    )


def _palavras_relevantes(
    texto: str,
) -> set[str]:
    palavras_ignoradas = {
        "qual",
        "quais",
        "como",
        "para",
        "pela",
        "pelo",
        "nosso",
        "nossa",
        "nossos",
        "nossas",
        "esse",
        "essa",
        "desse",
        "dessa",
        "produto",
        "produtos",
    }

    return {
        palavra
        for palavra in re.findall(
            r"[a-z0-9]+",
            texto,
        )
        if (
            len(palavra) >= 4
            and palavra not in palavras_ignoradas
        )
    }


def _pontuar_ferramenta(
    ferramenta: BaseTool,
    texto: str,
    categorias: list[str],
    intencao: str,
) -> int:
    nome = normalizar_texto(
        ferramenta.name.replace(
            "_",
            " ",
        )
    )

    descricao = normalizar_texto(
        ferramenta.description or ""
    )

    palavras = _palavras_relevantes(
        texto
    )

    pontuacao = 0

    for palavra in palavras:
        if palavra in nome:
            pontuacao += 5

        if palavra in descricao:
            pontuacao += 2

    for categoria in categorias:
        if categoria in nome:
            pontuacao += 4

        for termo in CONCEITOS.get(
            categoria,
            set(),
        ):
            if (
                termo in texto
                and termo in descricao
            ):
                pontuacao += 1

    if (
        intencao in {
            "leitura",
            "analise",
        }
        and _eh_ferramenta_leitura(
            ferramenta
        )
    ):
        pontuacao += 3

    if (
        intencao == "escrita"
        and _eh_ferramenta_escrita(
            ferramenta
        )
    ):
        pontuacao += 5

    # Favorece análises consolidadas em perguntas gerais.
    if (
        intencao == "analise"
        and "painel" in nome
        and _contem_algum(
            texto,
            TERMOS_EMPRESA_GERAL,
        )
    ):
        pontuacao += 8

    return pontuacao


def _selecionar_genericamente(
    texto: str,
    categorias: list[str],
    intencao: str,
) -> list[BaseTool]:
    if intencao == "conversa":
        return []

    categorias_expandidas = (
        _expandir_dependencias(
            categorias
        )
    )

    if (
        intencao == "analise"
        and not categorias_expandidas
    ):
        categorias_expandidas = [
            "analises",
        ]

    candidatas = _ferramentas_candidatas(
        categorias=categorias_expandidas,
        intencao=intencao,
    )

    if intencao == "escrita":
        candidatas = [
            ferramenta
            for ferramenta in candidatas
            if (
                _eh_ferramenta_leitura(
                    ferramenta
                )
                or _eh_ferramenta_escrita(
                    ferramenta
                )
            )
        ]

    pontuadas = [
        (
            _pontuar_ferramenta(
                ferramenta=ferramenta,
                texto=texto,
                categorias=(
                    categorias_expandidas
                ),
                intencao=intencao,
            ),
            ferramenta,
        )
        for ferramenta in candidatas
    ]

    pontuadas.sort(
        key=lambda item: (
            item[0],
            item[1].name,
        ),
        reverse=True,
    )

    ferramentas_positivas = [
        ferramenta
        for pontuacao, ferramenta in pontuadas
        if pontuacao > 0
    ]

    return ferramentas_positivas[
        :LIMITE_FERRAMENTAS_POR_REQUISICAO
    ]


# ============================================================
# CLASSIFICADOR LLM COMO FALLBACK
# ============================================================

def selecionar_ferramentas_intencao_classificada(
    intencao: str,
) -> list[BaseTool]:
    nomes = (
        FERRAMENTAS_POR_INTENCAO_CLASSIFICADA.get(
            intencao
        )
    )

    if not nomes:
        return []

    return _selecionar_ferramentas_por_nome(
        nomes
    )


def roteamento_precisa_classificador(
    resultado: ResultadoRoteamento,
) -> bool:
    """
    Classificador só é necessário quando:

    - nenhuma ferramenta foi encontrada;
    - ou o resultado ainda ficou excessivamente amplo.
    """

    quantidade = len(
        resultado.ferramentas
    )

    return (
        quantidade == 0
        or quantidade >= 6
    )


# ============================================================
# INTERFACE PÚBLICA
# ============================================================

def rotear_ferramentas(
    pergunta: str,
) -> ResultadoRoteamento:
    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    texto = normalizar_texto(
        pergunta_limpa
    )

    regra_alto_nivel = (
        _rotear_regra_alto_nivel(
            texto
        )
    )

    if regra_alto_nivel is not None:
        return regra_alto_nivel

    intencao = _detectar_intencao(
        texto
    )

    categorias = _detectar_categorias(
        texto
    )

    if (
        intencao == "analise"
        and not categorias
        and _contem_algum(
            texto,
            TERMOS_EMPRESA_GERAL,
        )
    ):
        categorias = [
            "analises",
        ]

    ferramentas = _selecionar_genericamente(
        texto=texto,
        categorias=categorias,
        intencao=intencao,
    )

    if intencao == "conversa":
        motivo = (
            "A pergunta não depende de dados empresariais."
        )

    elif ferramentas:
        motivo = (
            "Ferramentas selecionadas por relevância "
            f"para a intenção '{intencao}' e categorias: "
            f"{', '.join(categorias) or 'geral'}."
        )

    else:
        motivo = (
            "Não houve confiança suficiente no roteamento "
            "determinístico; o classificador poderá ser usado."
        )

    return ResultadoRoteamento(
        intencao=intencao,
        categorias=tuple(
            categorias
        ),
        ferramentas=tuple(
            ferramentas
        ),
        motivo=motivo,
    )


def selecionar_ferramentas(
    pergunta: str,
) -> list[BaseTool]:
    return list(
        rotear_ferramentas(
            pergunta
        ).ferramentas
    )


def diagnosticar_roteamento(
    pergunta: str,
) -> dict[str, object]:
    resultado = rotear_ferramentas(
        pergunta
    )

    return {
        "pergunta": pergunta,
        "intencao": resultado.intencao,
        "categorias": list(
            resultado.categorias
        ),
        "quantidade_ferramentas": len(
            resultado.ferramentas
        ),
        "ferramentas": (
            resultado.nomes_ferramentas
        ),
        "motivo": resultado.motivo,
    }


__all__ = [
    "LIMITE_FERRAMENTAS_POR_REQUISICAO",
    "ResultadoRoteamento",
    "diagnosticar_roteamento",
    "normalizar_texto",
    "rotear_ferramentas",
    "roteamento_precisa_classificador",
    "selecionar_ferramentas",
    "selecionar_ferramentas_intencao_classificada",
]