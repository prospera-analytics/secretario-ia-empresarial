from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal


TipoCorrespondencia = Literal[
    "exato",
    "equivalente",
    "muito_similar",
    "similar",
]

_PADRAO_PRECO_BRL = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)",
    flags=re.IGNORECASE,
)
_PADRAO_ARMAZENAMENTO = re.compile(
    r"\b(\d{2,4})\s*(?:gb|g)\b",
    flags=re.IGNORECASE,
)

_TERMOS_PRECO_PRINCIPAL = (
    "à vista", "a vista", "no pix", "via pix", "preço", "preco", "por", "oferta",
)
_TERMOS_PARCELA = (
    "parcela", "parcelas", "mensais", "por mês", "por mes", "x de",
)

_MARCAS_CONHECIDAS = {
    "apple", "samsung", "motorola", "xiaomi", "redmi", "poco", "asus", "realme",
    "honor", "nokia", "infinix", "tecno", "oppo", "vivo",
}
_VARIANTES = {
    "pro", "plus", "max", "mini", "ultra", "fe", "edge", "lite", "note", "fold", "flip",
}
_CORES = {
    "preto", "preta", "branco", "branca", "azul", "rosa", "verde", "cinza", "dourado",
    "dourada", "prata", "prateado", "prateada", "roxo", "roxa", "amarelo", "amarela",
    "vermelho", "vermelha", "grafite", "natural", "titanio", "titânio",
}
_TERMOS_COMERCIAIS = {
    "smartphone", "celular", "telefone", "gb", "g", "5g", "4g", "dual", "sim", "chip",
    "desbloqueado", "lacrado", "nacional", "original", "novo", "nova", "com", "sem", "de",
    "da", "do", "e", "para", "oferta", "promocao", "promoção", "camera", "câmera", "tela",
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

_JANELA_ANTES_PRECO = 360
_JANELA_DEPOIS_PRECO = 180
_CONFIANCA_MINIMA = Decimal("0.550")


@dataclass(frozen=True)
class PrecoExtraido:
    preco: Decimal
    moeda: str
    texto_original: str
    contexto: str
    pontuacao: int


@dataclass(frozen=True)
class CorrespondenciaProduto:
    tipo: TipoCorrespondencia
    pontuacao: Decimal
    diferencas: tuple[str, ...]


@dataclass(frozen=True)
class OfertaValidada:
    preco: Decimal
    moeda: str
    contexto: str
    confianca: Decimal
    correspondencia: TipoCorrespondencia
    pontuacao_preco: int
    diferencas: tuple[str, ...] = ()


def _normalizar_texto(texto: str) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    ).lower()
    separado = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", sem_acentos)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", separado).split())


def _converter_valor_brasileiro(valor_texto: str) -> Decimal | None:
    try:
        valor = Decimal(valor_texto.replace(".", "").replace(",", ".").strip())
    except InvalidOperation:
        return None
    return valor if valor > 0 else None


def _obter_contexto(texto: str, inicio: int, fim: int, tamanho: int = 90) -> str:
    return texto[max(0, inicio - tamanho):min(len(texto), fim + tamanho)].strip()


def _eh_valor_de_parcela(texto: str, inicio_preco: int) -> bool:
    trecho = texto[max(0, inicio_preco - 45):inicio_preco].lower()
    return bool(
        re.search(r"\b\d{1,2}\s*x\s*(?:de)?\s*$", trecho)
        or any(termo in trecho for termo in _TERMOS_PARCELA)
    )


def _calcular_pontuacao(contexto: str, posicao: int, origem: str, eh_parcela: bool) -> int:
    pontuacao = 3 if origem == "titulo" else 0
    contexto_minusculo = contexto.lower()
    pontuacao += 2 * sum(termo in contexto_minusculo for termo in _TERMOS_PRECO_PRINCIPAL)
    if eh_parcela:
        pontuacao -= 8
    if posicao < 250:
        pontuacao += 1
    return pontuacao


def _extrair_candidatos(texto: str, origem: str) -> list[PrecoExtraido]:
    candidatos: list[PrecoExtraido] = []
    for match in _PADRAO_PRECO_BRL.finditer(texto or ""):
        preco = _converter_valor_brasileiro(match.group(1))
        if preco is None:
            continue
        contexto = _obter_contexto(texto, match.start(), match.end())
        eh_parcela = _eh_valor_de_parcela(texto, match.start())
        candidatos.append(PrecoExtraido(
            preco=preco,
            moeda="BRL",
            texto_original=match.group(0),
            contexto=contexto,
            pontuacao=_calcular_pontuacao(contexto, match.start(), origem, eh_parcela),
        ))
    return candidatos


def extrair_preco_oferta(titulo: str, conteudo: str) -> PrecoExtraido | None:
    candidatos = [
        *_extrair_candidatos(titulo, "titulo"),
        *_extrair_candidatos(conteudo, "conteudo"),
    ]
    candidatos = [c for c in candidatos if c.pontuacao > -5]
    return max(candidatos, key=lambda c: (c.pontuacao, c.preco)) if candidatos else None


def _armazenamentos(texto: str) -> set[int]:
    return {int(valor) for valor in _PADRAO_ARMAZENAMENTO.findall(texto)}


def _variantes(tokens: set[str]) -> set[str]:
    return tokens & _VARIANTES


def _condicao(texto_normalizado: str) -> str | None:
    for termo, descricao in _CONDICOES_NAO_NOVAS.items():
        if termo in texto_normalizado:
            return descricao
    return None


def _tokens_relevantes(texto: str, armazenamento: int | None = None) -> set[str]:
    tokens = set(_normalizar_texto(texto).split())
    if armazenamento is not None:
        tokens.discard(str(armazenamento))
    return {
        token for token in tokens
        if token not in _TERMOS_COMERCIAIS and token not in _CORES and token not in _MARCAS_CONHECIDAS
    }


def avaliar_correspondencia_produto(
    nome_produto: str,
    marca: str,
    armazenamento_gb: int,
    titulo: str,
    contexto_produto: str,
) -> CorrespondenciaProduto | None:
    """Classifica um anúncio sem exigir igualdade textual absoluta."""
    esperado_texto = _normalizar_texto(f"{marca} {nome_produto}")
    encontrado_texto = _normalizar_texto(f"{titulo} {contexto_produto}")
    if not encontrado_texto:
        return None

    marca_tokens = set(_normalizar_texto(marca).split())
    encontrados = set(encontrado_texto.split())
    if not marca_tokens <= encontrados:
        return None

    esperados_modelo = _tokens_relevantes(esperado_texto, armazenamento_gb)
    encontrados_modelo = _tokens_relevantes(encontrado_texto)
    if not esperados_modelo:
        return None

    intersecao = esperados_modelo & encontrados_modelo
    cobertura_modelo = Decimal(len(intersecao)) / Decimal(len(esperados_modelo))
    if cobertura_modelo < Decimal("0.500"):
        return None

    variantes_esperadas = _variantes(set(esperado_texto.split()))
    variantes_encontradas = _variantes(encontrados)
    armazenamentos_encontrados = _armazenamentos(f"{titulo} {contexto_produto}")

    diferencas: list[str] = []
    mesma_variante = variantes_esperadas == variantes_encontradas
    if not mesma_variante:
        esperado = ", ".join(sorted(variantes_esperadas)) or "versão padrão"
        encontrado = ", ".join(sorted(variantes_encontradas)) or "versão padrão"
        diferencas.append(f"variante encontrada: {encontrado}; esperada: {esperado}")

    mesmo_armazenamento = armazenamento_gb in armazenamentos_encontrados
    if not mesmo_armazenamento:
        encontrado = ", ".join(f"{v} GB" for v in sorted(armazenamentos_encontrados)) or "não informado"
        diferencas.append(
            f"armazenamento encontrado: {encontrado}; esperado: {armazenamento_gb} GB"
        )

    condicao = _condicao(encontrado_texto)
    if condicao:
        diferencas.append(condicao)

    pontuacao = Decimal("0.200")  # marca
    pontuacao += cobertura_modelo * Decimal("0.450")
    pontuacao += Decimal("0.150") if mesma_variante else Decimal("0.050")
    pontuacao += Decimal("0.150") if mesmo_armazenamento else Decimal("0.050")
    pontuacao += Decimal("0.050") if condicao is None else Decimal("0.000")
    pontuacao = min(pontuacao, Decimal("1.000")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    titulo_normalizado = _normalizar_texto(titulo)
    esperado_sem_irrelevantes = _tokens_relevantes(esperado_texto, armazenamento_gb)
    titulo_sem_irrelevantes = _tokens_relevantes(titulo_normalizado, armazenamento_gb)

    if cobertura_modelo == 1 and mesma_variante and mesmo_armazenamento and condicao is None:
        tipo: TipoCorrespondencia = (
            "exato" if titulo_sem_irrelevantes == esperado_sem_irrelevantes else "equivalente"
        )
    elif cobertura_modelo >= Decimal("0.800") and condicao is None and (mesma_variante or mesmo_armazenamento):
        tipo = "muito_similar"
    else:
        tipo = "similar"

    if pontuacao < _CONFIANCA_MINIMA:
        return None

    return CorrespondenciaProduto(tipo=tipo, pontuacao=pontuacao, diferencas=tuple(diferencas))


def _janela_ao_redor_do_preco(texto: str, inicio: int, fim: int) -> str:
    return texto[
        max(0, inicio - _JANELA_ANTES_PRECO):
        min(len(texto), fim + _JANELA_DEPOIS_PRECO)
    ].strip()


def analisar_ofertas_produto(
    titulo: str,
    conteudo: str,
    nome_produto: str,
    marca: str,
    armazenamento_gb: int,
) -> list[OfertaValidada]:
    """Retorna preços de produtos exatos, equivalentes ou semelhantes."""
    if not conteudo.strip():
        return []

    ofertas: list[OfertaValidada] = []
    for match in _PADRAO_PRECO_BRL.finditer(conteudo):
        preco = _converter_valor_brasileiro(match.group(1))
        if preco is None or _eh_valor_de_parcela(conteudo, match.start()):
            continue

        janela = _janela_ao_redor_do_preco(conteudo, match.start(), match.end())
        correspondencia = avaliar_correspondencia_produto(
            nome_produto=nome_produto,
            marca=marca,
            armazenamento_gb=armazenamento_gb,
            titulo=titulo,
            contexto_produto=janela,
        )
        if correspondencia is None:
            continue

        contexto = _obter_contexto(conteudo, match.start(), match.end(), tamanho=110)
        candidato = PrecoExtraido(
            preco=preco,
            moeda="BRL",
            texto_original=match.group(0),
            contexto=contexto,
            pontuacao=_calcular_pontuacao(contexto, match.start(), "conteudo", False),
        )

        bonus_preco = Decimal("0.030") if any(
            termo in contexto.lower() for termo in _TERMOS_PRECO_PRINCIPAL
        ) else Decimal("0.000")
        confianca = min(
            Decimal("1.000"), correspondencia.pontuacao + bonus_preco
        ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        ofertas.append(OfertaValidada(
            preco=preco,
            moeda="BRL",
            contexto=contexto,
            confianca=confianca,
            correspondencia=correspondencia.tipo,
            pontuacao_preco=candidato.pontuacao,
            diferencas=correspondencia.diferencas,
        ))

    melhores: dict[tuple[Decimal, str], OfertaValidada] = {}
    for oferta in ofertas:
        chave = (oferta.preco, oferta.correspondencia)
        atual = melhores.get(chave)
        if atual is None or (oferta.confianca, oferta.pontuacao_preco) > (
            atual.confianca, atual.pontuacao_preco
        ):
            melhores[chave] = oferta

    ordem = {"exato": 4, "equivalente": 3, "muito_similar": 2, "similar": 1}
    return sorted(
        melhores.values(),
        key=lambda o: (ordem[o.correspondencia], o.confianca, o.pontuacao_preco),
        reverse=True,
    )
