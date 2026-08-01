"""
Memória factual estruturada da conversa.

A memória guarda somente entidades e resultados confirmados por
consultas ao banco ou por serviços externos. Ela não armazena
interpretações livres produzidas pelo modelo.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


VERSAO_MEMORIA = 1


def criar_memoria_vazia() -> dict[str, Any]:
    """
    Cria uma memória sem contexto factual confirmado.
    """

    return {
        "versao": VERSAO_MEMORIA,
        "produto": None,
        "concorrente": None,
        "ultima_oferta": None,
        "ultima_comparacao": None,
        "ultimo_fluxo": None,
        "ultima_intencao": None,
    }


def normalizar_memoria(
    memoria: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Garante que a memória possua sempre a estrutura esperada.

    Também cria uma cópia para impedir alterações acidentais
    no objeto original armazenado pelo Streamlit.
    """

    memoria_normalizada = criar_memoria_vazia()

    if not isinstance(memoria, Mapping):
        return memoria_normalizada

    for campo in (
        "produto",
        "concorrente",
        "ultima_oferta",
        "ultima_comparacao",
    ):
        valor = memoria.get(campo)

        if isinstance(valor, Mapping):
            memoria_normalizada[campo] = deepcopy(
                dict(valor)
            )

    for campo in (
        "ultimo_fluxo",
        "ultima_intencao",
    ):
        valor = memoria.get(campo)

        if isinstance(valor, str) and valor.strip():
            memoria_normalizada[campo] = valor.strip()

    return memoria_normalizada


def registrar_produto(
    memoria: Mapping[str, Any] | None,
    produto: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Registra como produto atual uma entidade confirmada.

    O produto deve ter, no mínimo, ID e nome.
    """

    produto_id = produto.get("id")
    produto_nome = produto.get("nome")

    if (
        not isinstance(produto_id, int)
        or produto_id <= 0
    ):
        raise ValueError(
            "O produto confirmado precisa possuir um ID válido."
        )

    if (
        not isinstance(produto_nome, str)
        or not produto_nome.strip()
    ):
        raise ValueError(
            "O produto confirmado precisa possuir um nome."
        )

    memoria_atualizada = normalizar_memoria(
        memoria
    )

    memoria_atualizada["produto"] = {
        "id": produto_id,
        "nome": produto_nome.strip(),
        "marca": produto.get("marca"),
        "armazenamento_gb": produto.get(
            "armazenamento_gb"
        ),
        "preco_venda": produto.get(
            "preco_venda"
        ),
        "ativo": produto.get("ativo"),
    }

    return memoria_atualizada


def registrar_concorrente(
    memoria: Mapping[str, Any] | None,
    concorrente: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Registra como concorrente atual uma entidade confirmada.
    """

    concorrente_id = concorrente.get("id")
    concorrente_nome = concorrente.get("nome")

    if (
        not isinstance(concorrente_id, int)
        or concorrente_id <= 0
    ):
        raise ValueError(
            "O concorrente confirmado precisa possuir um ID válido."
        )

    if (
        not isinstance(concorrente_nome, str)
        or not concorrente_nome.strip()
    ):
        raise ValueError(
            "O concorrente confirmado precisa possuir um nome."
        )

    memoria_atualizada = normalizar_memoria(
        memoria
    )

    memoria_atualizada["concorrente"] = {
        "id": concorrente_id,
        "nome": concorrente_nome.strip(),
        "dominio": concorrente.get("dominio"),
        "ativo": concorrente.get("ativo"),
    }

    return memoria_atualizada


def registrar_oferta(
    memoria: Mapping[str, Any] | None,
    oferta: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Registra uma oferta confirmada por ferramenta ou serviço.

    Nenhum preço, data ou URL é criado nesta função. Os valores são
    apenas copiados do resultado real recebido.
    """

    produto_id = oferta.get("produto_id")
    concorrente_id = oferta.get("concorrente_id")
    preco = oferta.get("preco")

    if (
        not isinstance(produto_id, int)
        or produto_id <= 0
    ):
        raise ValueError(
            "A oferta precisa possuir um produto_id válido."
        )

    if (
        not isinstance(concorrente_id, int)
        or concorrente_id <= 0
    ):
        raise ValueError(
            "A oferta precisa possuir um concorrente_id válido."
        )

    if not isinstance(
        preco,
        (int, float),
    ):
        raise ValueError(
            "A oferta precisa possuir um preço numérico."
        )

    memoria_atualizada = normalizar_memoria(
        memoria
    )

    memoria_atualizada["ultima_oferta"] = {
        "fonte": oferta.get("fonte"),
        "produto_id": produto_id,
        "produto_nome": oferta.get(
            "produto_nome"
        ),
        "concorrente_id": concorrente_id,
        "concorrente_nome": oferta.get(
            "concorrente_nome"
        ),
        "produto_encontrado": oferta.get(
            "produto_encontrado"
        ),
        "preco": preco,
        "moeda": oferta.get("moeda"),
        "correspondencia": oferta.get(
            "correspondencia"
        ),
        "similaridade": oferta.get(
            "similaridade"
        ),
        "url": oferta.get("url"),
        "coletado_em": oferta.get(
            "coletado_em"
        ),
        "diferencas": list(
            oferta.get("diferencas") or []
        ),
    }

    memoria_atualizada["ultimo_fluxo"] = (
        "consultar_preco_concorrente"
    )

    memoria_atualizada["ultima_intencao"] = (
        "consultar"
    )

    return memoria_atualizada


def registrar_comparacao(
    memoria: Mapping[str, Any] | None,
    comparacao: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Registra o resultado matemático de uma comparação confirmada.
    """

    memoria_atualizada = normalizar_memoria(
        memoria
    )

    memoria_atualizada["ultima_comparacao"] = {
        "produto_id": comparacao.get(
            "produto_id"
        ),
        "produto_nome": comparacao.get(
            "produto_nome"
        ),
        "concorrente_id": comparacao.get(
            "concorrente_id"
        ),
        "concorrente_nome": comparacao.get(
            "concorrente_nome"
        ),
        "preco_interno": comparacao.get(
            "preco_interno"
        ),
        "preco_concorrente": comparacao.get(
            "preco_concorrente"
        ),
        "diferenca_valor": comparacao.get(
            "diferenca_valor"
        ),
        "diferenca_percentual": comparacao.get(
            "diferenca_percentual"
        ),
        "url": comparacao.get("url"),
        "coletado_em": comparacao.get(
            "coletado_em"
        ),
    }

    memoria_atualizada["ultimo_fluxo"] = (
        "comparar_preco_concorrente"
    )

    memoria_atualizada["ultima_intencao"] = (
        "comparar"
    )

    return memoria_atualizada


def registrar_fluxo(
    memoria: Mapping[str, Any] | None,
    fluxo: str,
    intencao: str,
) -> dict[str, Any]:
    """
    Atualiza somente o fluxo e a intenção mais recentes.
    """

    fluxo_limpo = fluxo.strip()
    intencao_limpa = intencao.strip()

    if not fluxo_limpo:
        raise ValueError(
            "O nome do fluxo não pode estar vazio."
        )

    if not intencao_limpa:
        raise ValueError(
            "A intenção não pode estar vazia."
        )

    memoria_atualizada = normalizar_memoria(
        memoria
    )

    memoria_atualizada["ultimo_fluxo"] = fluxo_limpo
    memoria_atualizada["ultima_intencao"] = (
        intencao_limpa
    )

    return memoria_atualizada


def limpar_memoria() -> dict[str, Any]:
    """
    Remove todo o contexto factual da conversa.
    """

    return criar_memoria_vazia()


def resumir_memoria_para_modelo(
    memoria: Mapping[str, Any] | None,
) -> str:
    """
    Gera um contexto factual curto para o modelo.

    Somente dados confirmados são incluídos.
    Respostas anteriores do assistente não fazem parte do resumo.
    """

    memoria_atual = normalizar_memoria(
        memoria
    )

    linhas = [
        "CONTEXTO FACTUAL CONFIRMADO",
    ]

    produto = memoria_atual.get(
        "produto"
    )

    if isinstance(produto, Mapping):
        linhas.append(
            (
                "- Produto atual: "
                f"id={produto.get('id')}; "
                f"nome={produto.get('nome')}; "
                f"preço interno={produto.get('preco_venda')}."
            )
        )

    concorrente = memoria_atual.get(
        "concorrente"
    )

    if isinstance(concorrente, Mapping):
        linhas.append(
            (
                "- Concorrente atual: "
                f"id={concorrente.get('id')}; "
                f"nome={concorrente.get('nome')}; "
                f"domínio={concorrente.get('dominio')}."
            )
        )

    oferta = memoria_atual.get(
        "ultima_oferta"
    )

    if isinstance(oferta, Mapping):
        linhas.append(
            (
                "- Última oferta confirmada: "
                f"produto={oferta.get('produto_nome')}; "
                f"concorrente={oferta.get('concorrente_nome')}; "
                f"preço={oferta.get('preco')}; "
                f"correspondência={oferta.get('correspondencia')}; "
                f"URL={oferta.get('url')}; "
                f"coleta={oferta.get('coletado_em')}."
            )
        )

    comparacao = memoria_atual.get(
        "ultima_comparacao"
    )

    if isinstance(comparacao, Mapping):
        linhas.append(
            (
                "- Última comparação confirmada: "
                f"preço interno={comparacao.get('preco_interno')}; "
                f"preço concorrente="
                f"{comparacao.get('preco_concorrente')}; "
                f"diferença={comparacao.get('diferenca_valor')}; "
                f"percentual="
                f"{comparacao.get('diferenca_percentual')}%."
            )
        )

    ultimo_fluxo = memoria_atual.get(
        "ultimo_fluxo"
    )

    if ultimo_fluxo:
        linhas.append(
            f"- Último fluxo: {ultimo_fluxo}."
        )

    if len(linhas) == 1:
        linhas.append(
            "- Nenhum contexto factual foi confirmado."
        )

    linhas.extend(
        [
            "",
            (
                "Use apenas esses dados como memória factual. "
                "Não invente valores ausentes."
            ),
        ]
    )

    return "\n".join(
        linhas
    )

__all__ = [
    "criar_memoria_vazia",
    "limpar_memoria",
    "normalizar_memoria",
    "registrar_comparacao",
    "registrar_concorrente",
    "registrar_fluxo",
    "registrar_oferta",
    "registrar_produto",
    "resumir_memoria_para_modelo",
]