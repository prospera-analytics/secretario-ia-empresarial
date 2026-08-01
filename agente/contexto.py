"""
Resolução determinística de entidades e referências da conversa.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping

from crud.concorrente import listar_concorrentes
from crud.produto import (
    listar_produtos,
    pesquisar_produtos,
)
from database.conexao import SessionLocal


@dataclass(frozen=True)
class ContextoResolvido:
    produto: dict[str, Any] | None
    concorrente: dict[str, Any] | None
    usou_produto_memoria: bool
    usou_concorrente_memoria: bool
    ambiguidades: tuple[str, ...] = ()

    @property
    def completo_para_preco_concorrente(self) -> bool:
        return (
            self.produto is not None
            and self.concorrente is not None
        )


_TERMOS_REFERENCIA_PRODUTO = {
    "ele",
    "esse",
    "este",
    "esse produto",
    "este produto",
    "o produto",
    "nosso produto",
    "o nosso",
    "dele",
}


_TERMOS_REFERENCIA_CONCORRENTE = {
    "ela",
    "essa loja",
    "esse concorrente",
    "o concorrente",
    "a concorrente",
    "na mesma loja",
    "no mesmo concorrente",
}


_TERMOS_IRRELEVANTES_PRODUTO = {
    "qual",
    "quais",
    "preco",
    "precos",
    "valor",
    "valores",
    "atual",
    "atuais",
    "produto",
    "produtos",
    "nosso",
    "nossos",
    "loja",
    "concorrente",
    "concorrentes",
    "amazon",
    "magalu",
    "magazine",
    "luiza",
    "compare",
    "comparar",
    "comparacao",
    "como",
    "quanto",
    "custa",
    "esta",
}


def normalizar_texto(texto: str) -> str:
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


def _produto_para_dict(
    produto: Any,
) -> dict[str, Any]:
    return {
        "id": produto.id,
        "nome": produto.nome,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "preco_venda": float(
            produto.preco_venda
        ),
        "ativo": produto.ativo,
    }


def _concorrente_para_dict(
    concorrente: Any,
) -> dict[str, Any]:
    return {
        "id": concorrente.id,
        "nome": concorrente.nome,
        "dominio": concorrente.dominio,
        "ativo": concorrente.ativo,
    }


def _possui_referencia(
    texto: str,
    referencias: set[str],
) -> bool:
    return any(
        referencia in texto
        for referencia in referencias
    )


def _obter_entidade_memoria(
    memoria: Mapping[str, Any] | None,
    campo: str,
) -> dict[str, Any] | None:
    if not isinstance(
        memoria,
        Mapping,
    ):
        return None

    entidade = memoria.get(
        campo
    )

    if not isinstance(
        entidade,
        Mapping,
    ):
        return None

    entidade_dict = dict(
        entidade
    )

    entidade_id = entidade_dict.get(
        "id"
    )

    if (
        not isinstance(entidade_id, int)
        or entidade_id <= 0
    ):
        return None

    return entidade_dict


def _pontuar_produto(
    produto: Any,
    texto: str,
) -> int:
    nome = normalizar_texto(
        produto.nome
    )

    marca = normalizar_texto(
        produto.marca
    )

    tokens_pergunta = set(
        texto.split()
    )

    tokens_produto = set(
        nome.split()
    )

    pontuacao = 0

    if nome in texto:
        pontuacao += 100

    pontuacao += (
        len(
            tokens_pergunta
            & tokens_produto
        )
        * 10
    )

    if marca in tokens_pergunta:
        pontuacao += 5

    armazenamento = str(
        produto.armazenamento_gb
    )

    if armazenamento in tokens_pergunta:
        pontuacao += 15

    return pontuacao


def _resolver_produto_explicito(
    texto: str,
) -> tuple[
    dict[str, Any] | None,
    tuple[str, ...],
]:
    tokens_busca = [
        token
        for token in texto.split()
        if token not in _TERMOS_IRRELEVANTES_PRODUTO
        and len(token) >= 2
    ]

    termo_busca = " ".join(
        tokens_busca
    ).strip()

    with SessionLocal() as sessao:
        if termo_busca:
            encontrados = pesquisar_produtos(
                sessao=sessao,
                termo=termo_busca,
                apenas_ativos=True,
            )
        else:
            encontrados = listar_produtos(
                sessao=sessao,
                apenas_ativos=True,
            )

        if not encontrados:
            encontrados = listar_produtos(
                sessao=sessao,
                apenas_ativos=True,
            )

        pontuados = [
            (
                _pontuar_produto(
                    produto,
                    texto,
                ),
                produto,
            )
            for produto in encontrados
        ]

    pontuados = [
        item
        for item in pontuados
        if item[0] > 0
    ]

    if not pontuados:
        return None, ()

    pontuados.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    melhor_pontuacao = pontuados[0][0]

    melhores = [
        produto
        for pontuacao, produto in pontuados
        if pontuacao == melhor_pontuacao
    ]

    if len(melhores) > 1:
        nomes = tuple(
            produto.nome
            for produto in melhores
        )

        return (
            None,
            (
                "Produto ambíguo: "
                + ", ".join(nomes),
            ),
        )

    return (
        _produto_para_dict(
            melhores[0]
        ),
        (),
    )


def _resolver_concorrente_explicito(
    texto: str,
) -> tuple[
    dict[str, Any] | None,
    tuple[str, ...],
]:
    with SessionLocal() as sessao:
        concorrentes = listar_concorrentes(
            sessao=sessao,
            apenas_ativos=True,
        )

    correspondencias: list[Any] = []

    for concorrente in concorrentes:
        nome = normalizar_texto(
            concorrente.nome
        )

        dominio = normalizar_texto(
            concorrente.dominio
        )

        apelidos = {
            nome,
            dominio,
        }

        if "magazine luiza" in nome:
            apelidos.add(
                "magalu"
            )

        if "amazon" in nome:
            apelidos.add(
                "amazon"
            )

        if any(
            apelido in texto
            for apelido in apelidos
        ):
            correspondencias.append(
                concorrente
            )

    if not correspondencias:
        return None, ()

    if len(correspondencias) > 1:
        return (
            None,
            (
                "Concorrente ambíguo: "
                + ", ".join(
                    concorrente.nome
                    for concorrente
                    in correspondencias
                ),
            ),
        )

    return (
        _concorrente_para_dict(
            correspondencias[0]
        ),
        (),
    )


def resolver_contexto(
    pergunta: str,
    memoria: Mapping[str, Any] | None = None,
) -> ContextoResolvido:
    """
    Resolve produto e concorrente usando a pergunta e a memória.

    Entidades mencionadas explicitamente sempre têm prioridade.
    A memória é usada apenas quando a pergunta realmente depende
    de uma referência implícita ou não menciona uma nova entidade.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    texto = normalizar_texto(
        pergunta_limpa
    )

    produto_explicito, ambiguidades_produto = (
        _resolver_produto_explicito(
            texto
        )
    )

    concorrente_explicito, ambiguidades_concorrente = (
        _resolver_concorrente_explicito(
            texto
        )
    )

    produto_memoria = _obter_entidade_memoria(
        memoria,
        "produto",
    )

    concorrente_memoria = _obter_entidade_memoria(
        memoria,
        "concorrente",
    )

    usou_produto_memoria = False
    usou_concorrente_memoria = False

    produto = produto_explicito

    if (
        produto is None
        and produto_memoria is not None
        and (
            _possui_referencia(
                texto,
                _TERMOS_REFERENCIA_PRODUTO,
            )
            or not ambiguidades_produto
        )
    ):
        produto = produto_memoria
        usou_produto_memoria = True

    concorrente = concorrente_explicito

    if (
        concorrente is None
        and concorrente_memoria is not None
        and (
            _possui_referencia(
                texto,
                _TERMOS_REFERENCIA_CONCORRENTE,
            )
            or not ambiguidades_concorrente
        )
    ):
        concorrente = concorrente_memoria
        usou_concorrente_memoria = True

    return ContextoResolvido(
        produto=produto,
        concorrente=concorrente,
        usou_produto_memoria=(
            usou_produto_memoria
        ),
        usou_concorrente_memoria=(
            usou_concorrente_memoria
        ),
        ambiguidades=(
            *ambiguidades_produto,
            *ambiguidades_concorrente,
        ),
    )

def conversar_com_memoria(
    pergunta: str,
    memoria: Mapping[str, Any] | None = None,
    historico: Sequence[BaseMessage] | None = None,
    ferramentas: Sequence[BaseTool] | None = None,
) -> dict[str, Any]:
    """
    Executa primeiro os fluxos determinísticos.

    O agente com LLM é utilizado somente quando não existir um
    fluxo determinístico compatível com a pergunta.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    memoria_atual = normalizar_memoria(
        memoria
    )

    resultado_deterministico = (
        executar_fluxo_deterministico(
            pergunta=pergunta_limpa,
            memoria=memoria_atual,
        )
    )

    if resultado_deterministico.tratado:
        return {
            "resposta": (
                resultado_deterministico.resposta
                or "Consulta concluída."
            ),
            "memoria": (
                resultado_deterministico.memoria
            ),
            "fluxo": (
                resultado_deterministico.fluxo
            ),
            "dados": (
                resultado_deterministico.dados
            ),
            "deterministico": True,
        }

    resposta = conversar(
        pergunta=pergunta_limpa,
        historico=historico,
        ferramentas=ferramentas,
    )

    return {
        "resposta": resposta,
        "memoria": memoria_atual,
        "fluxo": None,
        "dados": None,
        "deterministico": False,
    }

__all__ = [
    "ContextoResolvido",
    "normalizar_texto",
    "resolver_contexto",
    "conversar_com_memoria"
]