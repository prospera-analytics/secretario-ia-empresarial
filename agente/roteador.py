"""
Roteamento seletivo de ferramentas do Secretário IA Empresarial.

O roteador analisa a pergunta do usuário e seleciona somente os grupos
de ferramentas necessários para atendê-la.

Ele não utiliza modelo de linguagem e, portanto, não gera uma chamada
adicional à API.
"""

import unicodedata
import re
from dataclasses import dataclass
from typing import Sequence

from langchain_core.tools import BaseTool

from agente.ferramentas.analises import FERRAMENTAS_ANALISES
from agente.ferramentas.campanha import FERRAMENTAS_CAMPANHA
from agente.ferramentas.compra import FERRAMENTAS_COMPRA
from agente.ferramentas.concorrente import FERRAMENTAS_CONCORRENTE
from agente.ferramentas.estoque import FERRAMENTAS_ESTOQUE
from agente.ferramentas.fornecedor import FERRAMENTAS_FORNECEDOR
from agente.ferramentas.preco_concorrente import (
    FERRAMENTAS_PRECO_CONCORRENTE,
)
from agente.ferramentas.produto import FERRAMENTAS_PRODUTO
from agente.ferramentas.venda import FERRAMENTAS_VENDA


LIMITE_FERRAMENTAS_POR_REQUISICAO = 25


@dataclass(frozen=True)
class ResultadoRoteamento:
    """Resultado produzido pelo roteador de ferramentas."""

    intencao: str
    categorias: tuple[str, ...]
    ferramentas: tuple[BaseTool, ...]
    motivo: str

    @property
    def nomes_ferramentas(self) -> list[str]:
        """Retorna apenas os nomes das ferramentas selecionadas."""

        return [
            ferramenta.name
            for ferramenta in self.ferramentas
        ]


GRUPOS_FERRAMENTAS: dict[str, Sequence[BaseTool]] = {
    "analises": FERRAMENTAS_ANALISES,
    "produto": FERRAMENTAS_PRODUTO,
    "estoque": FERRAMENTAS_ESTOQUE,
    "fornecedor": FERRAMENTAS_FORNECEDOR,
    "compra": FERRAMENTAS_COMPRA,
    "venda": FERRAMENTAS_VENDA,
    "campanha": FERRAMENTAS_CAMPANHA,
    "concorrente": FERRAMENTAS_CONCORRENTE,
    "preco_concorrente": FERRAMENTAS_PRECO_CONCORRENTE,
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

VERBOS_ESCRITA_REGEX = (
    r"cadastre|cadastrar|crie|criar|adicione|adicionar|"
    r"registre|registrar|atualize|atualizar|altere|alterar|"
    r"modifique|modificar|exclua|excluir|remova|remover|"
    r"desative|desativar|reative|reativar|ative|ativar|"
    r"cancele|cancelar|vender|compre|comprar"
)


ALVOS_ESCRITA_CATEGORIAS: dict[str, tuple[str, ...]] = {
    "produto": (
        "produto",
        "smartphone",
        "celular",
    ),
    "estoque": (
        "estoque",
        "saldo de estoque",
        "unidades no estoque",
    ),
    "fornecedor": (
        "fornecedor",
    ),
    "compra": (
        "compra",
        "pedido de compra",
    ),
    "venda": (
        "venda",
    ),
    "campanha": (
        "campanha",
        "promocao",
    ),
    "concorrente": (
        "concorrente",
    ),
    "preco_concorrente": (
        "preco concorrente",
        "preco da concorrencia",
    ),
}

def normalizar_texto(texto: str) -> str:
    """
    Converte o texto para minúsculas e remove acentos.

    Isso permite reconhecer igualmente termos como:

    - análise;
    - analise;
    - promoção;
    - promocao.
    """

    texto_sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFKD",
            texto,
        )
        if not unicodedata.combining(caractere)
    )

    return " ".join(
        texto_sem_acentos.lower().split()
    )


def _contem_algum(
    texto: str,
    palavras: set[str],
) -> bool:
    """Verifica se alguma expressão aparece no texto."""

    return any(
        palavra in texto
        for palavra in palavras
    )


def _pontuar_categoria(
    texto: str,
    categoria: str,
) -> int:
    """
    Calcula a relevância de uma categoria para a pergunta.
    """

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
    """Classifica a intenção principal da pergunta."""

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
        _pontuar_categoria(texto, categoria) > 0
        for categoria in PALAVRAS_CATEGORIAS
    ):
        return "leitura"

    return "conversa"


def _detectar_acoes_escrita(
    texto: str,
) -> tuple[str, ...]:
    """Identifica quais tipos de alteração foram solicitados."""

    acoes = [
        acao
        for acao, palavras in PALAVRAS_ACOES.items()
        if _contem_algum(texto, palavras)
    ]

    return tuple(acoes)


def _eh_ferramenta_leitura(
    ferramenta: BaseTool,
) -> bool:
    """Identifica ferramentas aparentemente somente de leitura."""

    nome = ferramenta.name.lower()

    return nome.startswith(
        PREFIXOS_LEITURA
    )


def _eh_ferramenta_escrita_compativel(
    ferramenta: BaseTool,
    acoes: tuple[str, ...],
) -> bool:
    """
    Verifica se a ferramenta realiza uma das ações solicitadas.
    """

    nome = ferramenta.name.lower()

    for acao in acoes:
        prefixos = ACOES_ESCRITA.get(
            acao,
            (),
        )

        if nome.startswith(prefixos):
            return True

    return False


def _remover_duplicadas(
    ferramentas: Sequence[BaseTool],
) -> list[BaseTool]:
    """Remove ferramentas repetidas usando o nome como chave."""

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


def _categorias_operacionais(
    texto: str,
) -> list[str]:
    """
    Retorna as categorias encontradas, ordenadas por relevância.
    """

    pontuacoes = {
        categoria: _pontuar_categoria(
            texto,
            categoria,
        )
        for categoria in PALAVRAS_CATEGORIAS
    }

    categorias = [
        categoria
        for categoria, pontuacao in pontuacoes.items()
        if pontuacao > 0
    ]

    categorias.sort(
        key=lambda categoria: pontuacoes[categoria],
        reverse=True,
    )

    return categorias


def _expandir_dependencias(
    categorias: list[str],
    texto: str,
) -> list[str]:
    """
    Adiciona categorias auxiliares necessárias para certas operações.

    Exemplos:

    - uma venda pode precisar localizar o produto e verificar estoque;
    - uma compra pode precisar localizar produto e fornecedor;
    - preço concorrente depende de concorrente e produto.
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
    Identifica a entidade que é alvo direto de uma operação de escrita.

    Exemplos:
    - "Registre uma venda do produto 1" -> venda
    - "Cadastre um produto" -> produto
    - "Adicione unidades ao estoque" -> estoque
    - "Desative o fornecedor 2" -> fornecedor
    """

    padroes_por_categoria: dict[str, tuple[str, ...]] = {
        "produto": (
            r"\b(?:cadastre|cadastrar|crie|criar|adicione|adicionar|"
            r"atualize|atualizar|altere|alterar|modifique|modificar|"
            r"exclua|excluir|remova|remover|desative|desativar|"
            r"reative|reativar)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\b(?:produto|smartphone|celular)\b",
        ),

        "estoque": (
            r"\b(?:crie|criar|adicione|adicionar|atualize|atualizar|"
            r"altere|alterar|modifique|modificar|remova|remover)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\b(?:estoque|unidades)\b",
        ),

        "fornecedor": (
            r"\b(?:cadastre|cadastrar|crie|criar|atualize|atualizar|"
            r"altere|alterar|modifique|modificar|desative|desativar|"
            r"reative|reativar|remova|remover)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\bfornecedor\b",
        ),

        "compra": (
            r"\b(?:registre|registrar|crie|criar|cancele|cancelar)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\bcompra\b",
            r"^\s*compre\b",
        ),

        "venda": (
            r"\b(?:registre|registrar|crie|criar|cancele|cancelar)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\bvenda\b",
            r"^\s*venda\b",
            r"^\s*vender\b",
        ),

        "campanha": (
            r"\b(?:cadastre|cadastrar|crie|criar|atualize|atualizar|"
            r"altere|alterar|ative|ativar|desative|desativar|"
            r"cancele|cancelar)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\b(?:campanha|promocao)\b",
        ),

        "concorrente": (
            r"\b(?:cadastre|cadastrar|crie|criar|atualize|atualizar|"
            r"altere|alterar|desative|desativar|reative|reativar)\b"
            r"(?:\s+\w+){0,3}\s+"
            r"\bconcorrente\b",
        ),

        "preco_concorrente": (
            r"\b(?:registre|registrar|cadastre|cadastrar|atualize|"
            r"atualizar|adicione|adicionar)\b"
            r"(?:\s+\w+){0,4}\s+"
            r"\bpreco(?:\s+do|\s+de)?\s+concorrente\b",
        ),
    }

    categorias_encontradas: list[str] = []

    for categoria, padroes in padroes_por_categoria.items():
        if any(
            re.search(padrao, texto)
            for padrao in padroes
        ):
            categorias_encontradas.append(categoria)

    return tuple(categorias_encontradas)


def _selecionar_por_intencao(
    intencao: str,
    categorias: list[str],
    texto: str,
) -> list[BaseTool]:
    """
    Seleciona ferramentas considerando intenção e categorias.

    Em operações de escrita, somente a categoria que representa
    o alvo da alteração recebe ferramentas modificadoras.

    As categorias auxiliares recebem apenas ferramentas de consulta.
    """

    if intencao == "conversa":
        return []

    if intencao == "analise":
        return list(
            FERRAMENTAS_ANALISES
        )

    if intencao == "leitura":
        ferramentas_leitura: list[BaseTool] = []

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

            ferramentas_leitura.extend(
                consultas if consultas else grupo
            )

        return _remover_duplicadas(
            ferramentas_leitura
        )

    categorias_alvo_escrita = (
        _detectar_categorias_alvo_escrita(
            texto
        )
    )

    acoes = _detectar_acoes_escrita(
        texto
    )

    ferramentas_resultado: list[BaseTool] = []

    for categoria in categorias:
        grupo = GRUPOS_FERRAMENTAS.get(
            categoria,
            (),
        )

        # Todas as categorias selecionadas podem fornecer consultas.
        ferramentas_resultado.extend(
            ferramenta
            for ferramenta in grupo
            if _eh_ferramenta_leitura(
                ferramenta
            )
        )

        # Somente a entidade explicitamente alterada recebe
        # ferramentas de escrita.
        if categoria not in categorias_alvo_escrita:
            continue

        ferramentas_resultado.extend(
            ferramenta
            for ferramenta in grupo
            if _eh_ferramenta_escrita_compativel(
                ferramenta,
                acoes,
            )
        )

    return _remover_duplicadas(
        ferramentas_resultado
    )


def _pontuar_ferramenta(
    ferramenta: BaseTool,
    texto: str,
    intencao: str,
) -> int:
    """
    Pontua ferramentas para aplicar o limite de segurança.

    A pontuação considera palavras presentes no nome e na descrição.
    """

    nome = normalizar_texto(
        ferramenta.name.replace("_", " ")
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
        and not _eh_ferramenta_leitura(ferramenta)
    ):
        pontuacao += 5

    if (
        intencao in {"leitura", "analise"}
        and _eh_ferramenta_leitura(ferramenta)
    ):
        pontuacao += 4

    return pontuacao


def _aplicar_limite(
    ferramentas: list[BaseTool],
    texto: str,
    intencao: str,
) -> list[BaseTool]:
    """
    Limita a quantidade de ferramentas enviada ao modelo.
    """

    if (
        len(ferramentas)
        <= LIMITE_FERRAMENTAS_POR_REQUISICAO
    ):
        return ferramentas

    ferramentas_ordenadas = sorted(
        ferramentas,
        key=lambda ferramenta: _pontuar_ferramenta(
            ferramenta,
            texto,
            intencao,
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
    Analisa uma pergunta e retorna as ferramentas apropriadas.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    texto = normalizar_texto(
        pergunta_limpa
    )

    intencao = _detectar_intencao(
        texto
    )

    categorias = _categorias_operacionais(
        texto
    )

    if intencao == "analise":
        categorias = ["analises"]

    elif (
        not categorias
        and _contem_algum(
            texto,
            PALAVRAS_EMPRESA_GERAL,
        )
    ):
        intencao = "analise"
        categorias = ["analises"]

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
        categorias=tuple(categorias),
        ferramentas=tuple(ferramentas),
        motivo=motivo,
    )


def selecionar_ferramentas(
    pergunta: str,
) -> list[BaseTool]:
    """
    Retorna somente a lista de ferramentas selecionadas.
    """

    return list(
        rotear_ferramentas(
            pergunta
        ).ferramentas
    )


def diagnosticar_roteamento(
    pergunta: str,
) -> dict[str, object]:
    """
    Retorna informações legíveis para testes e depuração.
    """

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