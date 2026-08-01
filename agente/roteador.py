"""
Roteamento seletivo de ferramentas do Secretário IA Empresarial.

O roteador utiliza regras determinísticas e não faz chamadas adicionais
a modelos de linguagem.

Fluxos críticos são tratados primeiro por regras de alto nível.
As demais perguntas seguem pelo roteamento genérico de categorias.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

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
    """Resultado produzido pelo roteador de ferramentas."""

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


PALAVRAS_CATEGORIAS: dict[str, set[str]] = {
    "produto": {
        "produto",
        "produtos",
        "smartphone",
        "smartphones",
        "celular",
        "celulares",
        "modelo",
        "modelos",
        "armazenamento",
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
        "ruptura",
        "cobertura",
        "estoque minimo",
    },
    "fornecedor": {
        "fornecedor",
        "fornecedores",
        "prazo de entrega",
        "entrega",
    },
    "compra": {
        "compra",
        "compras",
        "comprar",
        "adquirir",
        "pedido de compra",
        "pedidos de compra",
    },
    "venda": {
        "venda",
        "vendas",
        "vender",
        "faturamento",
        "receita",
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
        "loja concorrente",
        "lojas concorrentes",
        "amazon",
        "magalu",
        "magazine luiza",
    },
    "preco_concorrente": {
        "preco concorrente",
        "precos concorrentes",
        "preco da concorrencia",
        "precos da concorrencia",
        "menor preco",
        "comparar preco",
        "comparacao de preco",
    },
}


PALAVRAS_ANALITICAS = {
    "analise",
    "analisar",
    "diagnostico",
    "situacao geral",
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
    "margem de lucro",
    "lucro",
    "lucratividade",
    "desconto",
    "descontos",
    "reposicao",
    "repor",
    "ruptura",
    "cobertura",
    "recomendacao",
    "recomendar",
    "melhor fornecedor",
    "saude da empresa",
    "desempenho da empresa",
}


PALAVRAS_EMPRESA_GERAL = {
    "empresa",
    "negocio",
    "operacao",
    "operacoes",
    "gestao",
}


PALAVRAS_ESCRITA = {
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
    "venda",
    "vender",
    "compre",
    "comprar",
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
    "gerar_alertas",
)


ACOES_ESCRITA: dict[str, tuple[str, ...]] = {
    "criacao": (
        "cadastrar",
        "criar",
        "adicionar",
        "registrar",
    ),
    "atualizacao": (
        "atualizar",
        "alterar",
        "modificar",
    ),
    "exclusao": (
        "excluir",
        "remover",
        "desativar",
    ),
    "reativacao": (
        "reativar",
        "ativar",
    ),
    "cancelamento": (
        "cancelar",
    ),
}


PALAVRAS_ACOES: dict[str, set[str]] = {
    "criacao": {
        "cadastre",
        "cadastrar",
        "crie",
        "criar",
        "adicione",
        "adicionar",
        "registre",
        "registrar",
        "venda",
        "vender",
        "compre",
        "comprar",
    },
    "atualizacao": {
        "atualize",
        "atualizar",
        "altere",
        "alterar",
        "modifique",
        "modificar",
    },
    "exclusao": {
        "exclua",
        "excluir",
        "remova",
        "remover",
        "desative",
        "desativar",
    },
    "reativacao": {
        "reative",
        "reativar",
        "ative",
        "ativar",
    },
    "cancelamento": {
        "cancele",
        "cancelar",
    },
}


# ============================================================
# REGRAS DE ALTO NÍVEL
# ============================================================

_TERMOS_PRECO = {
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


_TERMOS_LOJAS_CONCORRENTES = {
    "concorrente",
    "concorrentes",
    "concorrencia",
    "amazon",
    "amazon brasil",
    "magalu",
    "magazine luiza",
}


_FERRAMENTAS_CONSULTA_PRECO_CONCORRENTE = {
    "pesquisar_smartphones",
    "consultar_concorrentes",
    "buscar_preco_atual_concorrente",
}


def normalizar_texto(
    texto: str,
) -> str:
    """
    Converte texto para minúsculas e remove acentos.
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
    palavras: set[str],
) -> bool:
    return any(
        palavra in texto
        for palavra in palavras
    )


def _remover_duplicadas(
    ferramentas: Sequence[BaseTool],
) -> list[BaseTool]:
    """
    Remove ferramentas repetidas pelo nome.
    """

    resultado: list[BaseTool] = []
    nomes_adicionados: set[str] = set()

    for ferramenta in ferramentas:
        if ferramenta.name in nomes_adicionados:
            continue

        nomes_adicionados.add(
            ferramenta.name
        )

        resultado.append(
            ferramenta
        )

    return resultado


def _selecionar_ferramentas_por_nome(
    nomes: set[str],
) -> list[BaseTool]:
    """
    Localiza somente as ferramentas explicitamente solicitadas.

    Regras críticas não devem enviar grupos completos ao modelo.
    """

    ferramentas: list[BaseTool] = []

    for grupo in GRUPOS_FERRAMENTAS.values():
        for ferramenta in grupo:
            if ferramenta.name in nomes:
                ferramentas.append(
                    ferramenta
                )

    ferramentas = _remover_duplicadas(
        ferramentas
    )

    nomes_encontrados = {
        ferramenta.name
        for ferramenta in ferramentas
    }

    nomes_ausentes = (
        nomes
        - nomes_encontrados
    )

    if nomes_ausentes:
        raise RuntimeError(
            "Ferramentas obrigatórias não encontradas: "
            + ", ".join(
                sorted(nomes_ausentes)
            )
        )

    return ferramentas


def _eh_consulta_preco_concorrente(
    texto: str,
) -> bool:
    """
    Detecta consulta de preço em uma loja concorrente.

    Exemplos:

    - Qual o preço do iPhone na Amazon?
    - Quanto custa no Magalu?
    - Compare nosso valor com o concorrente.
    - Atualize a oferta da Magazine Luiza.
    """

    possui_termo_preco = _contem_algum(
        texto,
        _TERMOS_PRECO,
    )

    possui_loja_concorrente = _contem_algum(
        texto,
        _TERMOS_LOJAS_CONCORRENTES,
    )

    return (
        possui_termo_preco
        and possui_loja_concorrente
    )


def _rotear_regra_alto_nivel(
    texto: str,
) -> ResultadoRoteamento | None:
    """
    Aplica regras determinísticas para fluxos críticos.

    Estas regras são avaliadas antes do roteamento genérico.
    """

    if _eh_consulta_preco_concorrente(
        texto
    ):
        ferramentas = (
            _selecionar_ferramentas_por_nome(
                _FERRAMENTAS_CONSULTA_PRECO_CONCORRENTE
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

    return None


# ============================================================
# ROTEAMENTO GENÉRICO
# ============================================================

def _pontuar_categoria(
    texto: str,
    categoria: str,
) -> int:
    palavras = PALAVRAS_CATEGORIAS.get(
        categoria,
        set(),
    )

    return sum(
        1
        for palavra in palavras
        if palavra in texto
    )


def _detectar_intencao(
    texto: str,
) -> str:
    possui_escrita = _contem_algum(
        texto,
        PALAVRAS_ESCRITA,
    )

    possui_analise = _contem_algum(
        texto,
        PALAVRAS_ANALITICAS,
    )

    if possui_escrita:
        return "escrita"

    if possui_analise:
        return "analise"

    if any(
        _pontuar_categoria(
            texto,
            categoria,
        ) > 0
        for categoria in PALAVRAS_CATEGORIAS
    ):
        return "leitura"

    return "conversa"


def _detectar_acoes_escrita(
    texto: str,
) -> tuple[str, ...]:
    return tuple(
        acao
        for acao, palavras
        in PALAVRAS_ACOES.items()
        if _contem_algum(
            texto,
            palavras,
        )
    )


def _eh_ferramenta_leitura(
    ferramenta: BaseTool,
) -> bool:
    return ferramenta.name.lower().startswith(
        PREFIXOS_LEITURA
    )


def _eh_ferramenta_escrita_compativel(
    ferramenta: BaseTool,
    acoes: tuple[str, ...],
) -> bool:
    nome = ferramenta.name.lower()

    for acao in acoes:
        prefixos = ACOES_ESCRITA.get(
            acao,
            (),
        )

        if nome.startswith(prefixos):
            return True

    return False


def _categorias_operacionais(
    texto: str,
) -> list[str]:
    pontuacoes = {
        categoria: _pontuar_categoria(
            texto,
            categoria,
        )
        for categoria in PALAVRAS_CATEGORIAS
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


def _expandir_dependencias(
    categorias: list[str],
    texto: str,
) -> list[str]:
    """
    Adiciona categorias auxiliares necessárias.
    """

    resultado = list(categorias)

    if "venda" in resultado:
        resultado.extend(
            [
                "produto",
                "estoque",
            ]
        )

    if "compra" in resultado:
        resultado.extend(
            [
                "produto",
                "fornecedor",
                "estoque",
            ]
        )

    if "campanha" in resultado:
        resultado.append(
            "produto"
        )

    if "preco_concorrente" in resultado:
        resultado.extend(
            [
                "produto",
                "concorrente",
            ]
        )

    if (
        "fornecedor" in resultado
        and "reposicao" in texto
    ):
        resultado.extend(
            [
                "produto",
                "estoque",
                "analises",
            ]
        )

    return list(
        dict.fromkeys(resultado)
    )


def _detectar_categorias_alvo_escrita(
    texto: str,
) -> tuple[str, ...]:
    """
    Identifica a entidade alterada diretamente.
    """

    padroes: dict[
        str,
        tuple[str, ...],
    ] = {
        "produto": (
            (
                r"\b(?:cadastre|cadastrar|crie|criar|"
                r"adicione|adicionar|atualize|atualizar|"
                r"altere|alterar|modifique|modificar|"
                r"exclua|excluir|remova|remover|"
                r"desative|desativar|reative|reativar)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\b(?:produto|smartphone|celular)\b"
            ),
        ),
        "estoque": (
            (
                r"\b(?:crie|criar|adicione|adicionar|"
                r"atualize|atualizar|altere|alterar|"
                r"modifique|modificar|remova|remover)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\b(?:estoque|unidades)\b"
            ),
        ),
        "fornecedor": (
            (
                r"\b(?:cadastre|cadastrar|crie|criar|"
                r"atualize|atualizar|altere|alterar|"
                r"modifique|modificar|desative|desativar|"
                r"reative|reativar|remova|remover)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\bfornecedor\b"
            ),
        ),
        "compra": (
            (
                r"\b(?:registre|registrar|crie|criar|"
                r"cancele|cancelar)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\bcompra\b"
            ),
            r"^\s*compre\b",
        ),
        "venda": (
            (
                r"\b(?:registre|registrar|crie|criar|"
                r"cancele|cancelar)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\bvenda\b"
            ),
            r"^\s*venda\b",
            r"^\s*vender\b",
        ),
        "campanha": (
            (
                r"\b(?:cadastre|cadastrar|crie|criar|"
                r"atualize|atualizar|altere|alterar|"
                r"ative|ativar|desative|desativar|"
                r"cancele|cancelar)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\b(?:campanha|promocao)\b"
            ),
        ),
        "concorrente": (
            (
                r"\b(?:cadastre|cadastrar|crie|criar|"
                r"atualize|atualizar|altere|alterar|"
                r"desative|desativar|reative|reativar)\b"
                r"(?:\s+\w+){0,3}\s+"
                r"\bconcorrente\b"
            ),
        ),
        "preco_concorrente": (
            (
                r"\b(?:registre|registrar|cadastre|"
                r"cadastrar|atualize|atualizar|"
                r"adicione|adicionar)\b"
                r"(?:\s+\w+){0,4}\s+"
                r"\bpreco(?:\s+do|\s+de)?"
                r"\s+concorrente\b"
            ),
        ),
    }

    categorias_encontradas = [
        categoria
        for categoria, expressoes
        in padroes.items()
        if any(
            re.search(
                expressao,
                texto,
            )
            for expressao in expressoes
        )
    ]

    return tuple(
        categorias_encontradas
    )


def _selecionar_por_intencao(
    intencao: str,
    categorias: list[str],
    texto: str,
) -> list[BaseTool]:
    if intencao == "conversa":
        return []

    if intencao == "analise":
        return list(
            FERRAMENTAS_ANALISES
        )

    if intencao == "leitura":
        ferramentas: list[BaseTool] = []

        for categoria in categorias:
            grupo = GRUPOS_FERRAMENTAS.get(
                categoria,
                (),
            )

            consultas = [
                ferramenta
                for ferramenta in grupo
                if _eh_ferramenta_leitura(
                    ferramenta
                )
            ]

            ferramentas.extend(
                consultas or grupo
            )

        return _remover_duplicadas(
            ferramentas
        )

    categorias_alvo = (
        _detectar_categorias_alvo_escrita(
            texto
        )
    )

    acoes = _detectar_acoes_escrita(
        texto
    )

    ferramentas: list[BaseTool] = []

    for categoria in categorias:
        grupo = GRUPOS_FERRAMENTAS.get(
            categoria,
            (),
        )

        ferramentas.extend(
            ferramenta
            for ferramenta in grupo
            if _eh_ferramenta_leitura(
                ferramenta
            )
        )

        if categoria not in categorias_alvo:
            continue

        ferramentas.extend(
            ferramenta
            for ferramenta in grupo
            if _eh_ferramenta_escrita_compativel(
                ferramenta,
                acoes,
            )
        )

    return _remover_duplicadas(
        ferramentas
    )


def _pontuar_ferramenta(
    ferramenta: BaseTool,
    texto: str,
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

    palavras_pergunta = {
        palavra
        for palavra in texto.split()
        if len(palavra) >= 4
    }

    pontuacao = sum(
        3
        for palavra in palavras_pergunta
        if palavra in nome
    )

    pontuacao += sum(
        1
        for palavra in palavras_pergunta
        if palavra in descricao
    )

    if (
        intencao == "escrita"
        and not _eh_ferramenta_leitura(
            ferramenta
        )
    ):
        pontuacao += 5

    if (
        intencao in {
            "leitura",
            "analise",
        }
        and _eh_ferramenta_leitura(
            ferramenta
        )
    ):
        pontuacao += 4

    return pontuacao


def _aplicar_limite(
    ferramentas: list[BaseTool],
    texto: str,
    intencao: str,
) -> list[BaseTool]:
    if (
        len(ferramentas)
        <= LIMITE_FERRAMENTAS_POR_REQUISICAO
    ):
        return ferramentas

    ferramentas_ordenadas = sorted(
        ferramentas,
        key=lambda ferramenta: (
            _pontuar_ferramenta(
                ferramenta,
                texto,
                intencao,
            )
        ),
        reverse=True,
    )

    return ferramentas_ordenadas[
        :LIMITE_FERRAMENTAS_POR_REQUISICAO
    ]


def rotear_ferramentas(
    pergunta: str,
) -> ResultadoRoteamento:
    """
    Analisa uma pergunta e retorna somente as ferramentas necessárias.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    texto = normalizar_texto(
        pergunta_limpa
    )

    resultado_alto_nivel = (
        _rotear_regra_alto_nivel(
            texto
        )
    )

    if resultado_alto_nivel is not None:
        return resultado_alto_nivel

    intencao = _detectar_intencao(
        texto
    )

    categorias = _categorias_operacionais(
        texto
    )

    if intencao == "analise":
        categorias = [
            "analises"
        ]

    elif (
        not categorias
        and _contem_algum(
            texto,
            PALAVRAS_EMPRESA_GERAL,
        )
    ):
        intencao = "analise"
        categorias = [
            "analises"
        ]

    categorias = _expandir_dependencias(
        categorias,
        texto,
    )

    ferramentas = _selecionar_por_intencao(
        intencao=intencao,
        categorias=categorias,
        texto=texto,
    )

    ferramentas = _aplicar_limite(
        ferramentas=ferramentas,
        texto=texto,
        intencao=intencao,
    )

    if intencao == "conversa":
        motivo = (
            "A pergunta não depende de dados empresariais."
        )
    else:
        motivo = (
            "Ferramentas selecionadas conforme a intenção "
            f"'{intencao}' e as categorias: "
            f"{', '.join(categorias)}."
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
    "selecionar_ferramentas",
]