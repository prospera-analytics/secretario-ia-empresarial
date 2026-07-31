from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from web.concorrentes import (
    extrair_preco_concorrente,
)


TipoCorrespondencia = Literal[
    "exato",
    "equivalente",
    "muito_similar",
    "similar",
]


_PADRAO_ARMAZENAMENTO = re.compile(
    r"\b(\d{2,4})\s*(?:gb|g)\b",
    flags=re.IGNORECASE,
)


_MARCAS_CONHECIDAS = {
    "apple",
    "samsung",
    "motorola",
    "xiaomi",
    "redmi",
    "poco",
    "asus",
    "realme",
    "honor",
    "nokia",
    "infinix",
    "tecno",
    "oppo",
    "vivo",
}


_VARIANTES = {
    "pro",
    "plus",
    "max",
    "mini",
    "ultra",
    "fe",
    "edge",
    "lite",
    "note",
    "fold",
    "flip",
}


_CORES = {
    "preto",
    "preta",
    "branco",
    "branca",
    "azul",
    "rosa",
    "verde",
    "cinza",
    "dourado",
    "dourada",
    "prata",
    "prateado",
    "prateada",
    "roxo",
    "roxa",
    "amarelo",
    "amarela",
    "vermelho",
    "vermelha",
    "grafite",
    "natural",
    "titanio",
    "titânio",
}


_TERMOS_COMERCIAIS = {
    "smartphone",
    "celular",
    "telefone",
    "gb",
    "g",
    "5g",
    "4g",
    "dual",
    "sim",
    "chip",
    "desbloqueado",
    "lacrado",
    "nacional",
    "original",
    "novo",
    "nova",
    "com",
    "sem",
    "de",
    "da",
    "do",
    "e",
    "para",
    "oferta",
    "promocao",
    "promoção",
    "camera",
    "câmera",
    "tela",
}


_CONDICOES_NAO_NOVAS = {
    "usado": "produto usado",
    "usada": "produto usado",
    "seminovo": "produto seminovo",
    "seminova": "produto seminovo",
    "recondicionado": "produto recondicionado",
    "recondicionada": "produto recondicionado",
    "reembalado": "produto reembalado",
    "reembalada": "produto reembalado",
    "open box": "produto open box",
}


_CONFIANCA_MINIMA = Decimal("0.550")

# Evita usar toda a página na validação do produto, pois páginas de lojas
# frequentemente contêm produtos relacionados, acessórios e recomendações.
_LIMITE_CONTEXTO_PRODUTO = 2500


@dataclass(frozen=True)
class CorrespondenciaProduto:
    tipo: TipoCorrespondencia
    pontuacao: Decimal
    diferencas: tuple[str, ...]


@dataclass(frozen=True)
class OfertaValidada:
    preco: Decimal
    moeda: str
    modalidade: str
    correspondencia: TipoCorrespondencia
    confianca: Decimal
    diferencas: tuple[str, ...] = ()


def _normalizar_texto(
    texto: str,
) -> str:
    """
    Normaliza texto para comparação de produtos.

    Também separa letras e números:

    iPhone16e -> iphone 16 e
    """

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


def _armazenamentos(
    texto: str,
) -> set[int]:
    """
    Retorna os armazenamentos explicitamente encontrados.

    Exemplos:

    128 GB -> 128
    256G   -> 256
    """

    return {
        int(valor)
        for valor in _PADRAO_ARMAZENAMENTO.findall(
            texto
        )
    }


def _variantes(
    tokens: set[str],
) -> set[str]:
    return tokens & _VARIANTES


def _variantes_modelo(
    texto_normalizado: str,
) -> set[str]:
    """
    Identifica variantes explícitas do modelo.

    A letra "e" só é tratada como variante quando aparece
    imediatamente depois de um número.

    Assim:

    iPhone 16e -> variante "e"

    enquanto:

    iPhone 16 e carregador

    não deve transformar a conjunção em variante.
    """

    tokens = set(
        texto_normalizado.split()
    )

    variantes = _variantes(
        tokens
    )

    if re.search(
        r"\b\d+\s+e\b",
        texto_normalizado,
    ):
        variantes.add(
            "e"
        )

    return variantes


def _condicao(
    texto_normalizado: str,
) -> str | None:
    """
    Detecta produtos que não são anunciados como novos.
    """

    for termo, descricao in (
        _CONDICOES_NAO_NOVAS.items()
    ):
        termo_normalizado = _normalizar_texto(
            termo
        )

        if re.search(
            rf"\b{re.escape(termo_normalizado)}\b",
            texto_normalizado,
        ):
            return descricao

    return None


def _tokens_relevantes(
    texto: str,
    armazenamento: int | None = None,
) -> set[str]:
    """
    Remove termos comerciais, cores e marcas da comparação
    principal do modelo.
    """

    tokens = set(
        _normalizar_texto(
            texto
        ).split()
    )

    if armazenamento is not None:
        tokens.discard(
            str(armazenamento)
        )

    return {
        token
        for token in tokens
        if token not in _TERMOS_COMERCIAIS
        and token not in _CORES
        and token not in _MARCAS_CONHECIDAS
    }


def avaliar_correspondencia_produto(
    nome_produto: str,
    marca: str,
    armazenamento_gb: int,
    titulo: str,
    contexto_produto: str,
) -> CorrespondenciaProduto | None:
    """
    Verifica se a página corresponde ao smartphone procurado.

    Compara:

    - marca;
    - modelo;
    - variante;
    - armazenamento;
    - condição do produto.

    Ignora:

    - cores;
    - palavras comerciais;
    - adjetivos de marketing.
    """

    esperado_texto = _normalizar_texto(
        f"{marca} {nome_produto}"
    )

    encontrado_texto = _normalizar_texto(
        f"{titulo} {contexto_produto}"
    )

    if not encontrado_texto:
        return None

    marca_tokens = set(
        _normalizar_texto(
            marca
        ).split()
    )

    tokens_encontrados = set(
        encontrado_texto.split()
    )

    if not marca_tokens <= tokens_encontrados:
        return None

    tokens_modelo_esperado = _tokens_relevantes(
        esperado_texto,
        armazenamento_gb,
    )

    tokens_modelo_encontrado = _tokens_relevantes(
        encontrado_texto
    )

    if not tokens_modelo_esperado:
        return None

    intersecao = (
        tokens_modelo_esperado
        & tokens_modelo_encontrado
    )

    cobertura_modelo = (
        Decimal(
            len(intersecao)
        )
        / Decimal(
            len(tokens_modelo_esperado)
        )
    )

    if cobertura_modelo < Decimal("0.500"):
        return None

    variantes_esperadas = _variantes_modelo(
        esperado_texto
    )

    variantes_encontradas = _variantes_modelo(
        encontrado_texto
    )

    # Uma variante diferente significa outro produto.
    # Exemplo: iPhone 16 não corresponde a iPhone 16e.
    if (
        variantes_esperadas
        != variantes_encontradas
    ):
        return None

    armazenamentos_encontrados = (
        _armazenamentos(
            f"{titulo} {contexto_produto}"
        )
    )

    mesmo_armazenamento = (
        armazenamento_gb
        in armazenamentos_encontrados
    )

    diferencas: list[str] = []

    if not mesmo_armazenamento:
        armazenamento_encontrado = (
            ", ".join(
                f"{valor} GB"
                for valor in sorted(
                    armazenamentos_encontrados
                )
            )
            or "não informado"
        )

        diferencas.append(
            "armazenamento encontrado: "
            f"{armazenamento_encontrado}; "
            f"esperado: {armazenamento_gb} GB"
        )

    condicao_encontrada = _condicao(
        encontrado_texto
    )

    if condicao_encontrada:
        diferencas.append(
            condicao_encontrada
        )

    pontuacao = Decimal("0.200")

    pontuacao += (
        cobertura_modelo
        * Decimal("0.450")
    )

    # A igualdade das variantes já foi exigida acima.
    pontuacao += Decimal("0.150")

    pontuacao += (
        Decimal("0.150")
        if mesmo_armazenamento
        else Decimal("0.050")
    )

    pontuacao += (
        Decimal("0.050")
        if condicao_encontrada is None
        else Decimal("0.000")
    )

    pontuacao = min(
        pontuacao,
        Decimal("1.000"),
    ).quantize(
        Decimal("0.001"),
        rounding=ROUND_HALF_UP,
    )

    titulo_normalizado = _normalizar_texto(
        titulo
    )

    esperado_sem_irrelevantes = (
        _tokens_relevantes(
            esperado_texto,
            armazenamento_gb,
        )
    )

    titulo_sem_irrelevantes = (
        _tokens_relevantes(
            titulo_normalizado,
            armazenamento_gb,
        )
    )

    if (
        cobertura_modelo == Decimal("1")
        and mesmo_armazenamento
        and condicao_encontrada is None
    ):
        tipo: TipoCorrespondencia = (
            "exato"
            if titulo_sem_irrelevantes
            == esperado_sem_irrelevantes
            else "equivalente"
        )

    elif (
        cobertura_modelo
        >= Decimal("0.800")
        and condicao_encontrada is None
    ):
        tipo = "muito_similar"

    else:
        tipo = "similar"

    if pontuacao < _CONFIANCA_MINIMA:
        return None

    return CorrespondenciaProduto(
        tipo=tipo,
        pontuacao=pontuacao,
        diferencas=tuple(
            diferencas
        ),
    )


def analisar_oferta_produto(
    dominio: str,
    titulo: str,
    conteudo: str,
    nome_produto: str,
    marca: str,
    armazenamento_gb: int,
) -> OfertaValidada | None:
    """
    Valida uma página de produto e extrai um único preço explícito.

    Fluxo:

    1. valida a correspondência do produto;
    2. seleciona o extrator da loja;
    3. extrai um único preço explicitamente publicado;
    4. retorna a oferta validada.

    O serviço não:

    - procura vários candidatos monetários;
    - calcula descontos;
    - soma parcelas;
    - infere preços;
    - escolhe valores por pontuação.
    """

    if not isinstance(
        titulo,
        str,
    ):
        return None

    if not isinstance(
        conteudo,
        str,
    ):
        return None

    titulo = titulo.strip()
    conteudo = conteudo.strip()

    if not titulo and not conteudo:
        return None

    contexto_produto = conteudo[
        :_LIMITE_CONTEXTO_PRODUTO
    ]

    correspondencia = (
        avaliar_correspondencia_produto(
            nome_produto=nome_produto,
            marca=marca,
            armazenamento_gb=armazenamento_gb,
            titulo=titulo,
            contexto_produto=contexto_produto,
        )
    )

    if correspondencia is None:
        return None

    preco_extraido = (
        extrair_preco_concorrente(
            dominio=dominio,
            conteudo=conteudo,
        )
    )

    if preco_extraido is None:
        return None

    return OfertaValidada(
        preco=preco_extraido.valor,
        moeda="BRL",
        modalidade=preco_extraido.modalidade,
        correspondencia=correspondencia.tipo,
        confianca=correspondencia.pontuacao,
        diferencas=correspondencia.diferencas,
    )


__all__ = [
    "TipoCorrespondencia",
    "CorrespondenciaProduto",
    "OfertaValidada",
    "avaliar_correspondencia_produto",
    "analisar_oferta_produto",
]