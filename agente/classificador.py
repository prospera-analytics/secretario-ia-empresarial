"""
Classificação econômica de intenções empresariais.

Este módulo é usado somente quando as regras determinísticas
não conseguem selecionar ferramentas com confiança suficiente.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

from agente.modelo import criar_modelo


INTENCOES_SUPORTADAS = {
    "recomendacao_fornecedor",
    "risco_estoque",
    "consulta_estoque",
    "analise_vendas",
    "consulta_compras",
    "analise_margem",
    "analise_empresa",
    "consulta_produto",
    "consulta_fornecedor",
    "consulta_concorrente",
    "conversa",
    "esclarecimento",
}


@dataclass(frozen=True)
class ResultadoClassificacao:
    """
    Resultado validado da classificação de intenção.
    """

    intencao: str
    confianca: float
    motivo: str

    @property
    def confiavel(self) -> bool:
        return self.confianca >= 0.72


def _contexto_compacto(
    memoria: Mapping[str, Any] | None,
) -> str:
    """
    Inclui somente entidades confirmadas relevantes ao roteamento.
    """

    if not isinstance(memoria, Mapping):
        return "Nenhum contexto factual confirmado."

    partes: list[str] = []

    produto = memoria.get("produto")

    if isinstance(produto, Mapping):
        partes.append(
            (
                "Produto atual confirmado: "
                f"id={produto.get('id')}; "
                f"nome={produto.get('nome')}."
            )
        )

    concorrente = memoria.get("concorrente")

    if isinstance(concorrente, Mapping):
        partes.append(
            (
                "Concorrente atual confirmado: "
                f"id={concorrente.get('id')}; "
                f"nome={concorrente.get('nome')}."
            )
        )

    if not partes:
        return "Nenhum contexto factual confirmado."

    return "\n".join(partes)


def _extrair_texto(
    conteudo: Any,
) -> str:
    if isinstance(conteudo, str):
        return conteudo.strip()

    if isinstance(conteudo, list):
        partes: list[str] = []

        for bloco in conteudo:
            if isinstance(bloco, str):
                partes.append(bloco)
                continue

            if isinstance(bloco, Mapping):
                texto = bloco.get("text")

                if texto:
                    partes.append(str(texto))

        return "\n".join(partes).strip()

    return str(conteudo or "").strip()


def _validar_resultado(
    dados: Any,
) -> ResultadoClassificacao:
    if not isinstance(dados, Mapping):
        raise ValueError(
            "O classificador não retornou um objeto JSON."
        )

    intencao = str(
        dados.get("intencao", "")
    ).strip()

    if intencao not in INTENCOES_SUPORTADAS:
        raise ValueError(
            f"Intenção inválida: {intencao!r}."
        )

    try:
        confianca = float(
            dados.get("confianca", 0)
        )
    except (TypeError, ValueError) as erro:
        raise ValueError(
            "A confiança retornada não é numérica."
        ) from erro

    confianca = max(
        0.0,
        min(1.0, confianca),
    )

    motivo = str(
        dados.get("motivo", "")
    ).strip()

    return ResultadoClassificacao(
        intencao=intencao,
        confianca=confianca,
        motivo=motivo,
    )


def classificar_intencao(
    pergunta: str,
    memoria: Mapping[str, Any] | None = None,
) -> ResultadoClassificacao:
    """
    Classifica a intenção usando uma chamada curta ao modelo.

    Não recebe schemas de ferramentas, histórico completo,
    resultados do banco nem o prompt principal do agente.
    """

    pergunta_limpa = pergunta.strip()

    if not pergunta_limpa:
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    contexto = _contexto_compacto(
        memoria
    )

    instrucoes = """
Você é um classificador de intenções de um sistema empresarial.

Retorne exclusivamente um objeto JSON com:
- intencao;
- confianca, entre 0 e 1;
- motivo, com no máximo 20 palavras.

Intenções permitidas:

recomendacao_fornecedor:
escolher fornecedor, distribuidor ou parceiro para comprar,
repor ou fazer pedido considerando custo, prazo, estoque,
vendas ou compras pendentes.

risco_estoque:
avaliar ruptura, cobertura, demanda, vendas recentes ou
quantidade ideal de reposição.

consulta_estoque:
consultar quantidades, menores estoques, estoque mínimo ou
produtos em falta.

analise_vendas:
analisar vendas, demanda, receita, produtos mais vendidos ou
desempenho comercial.

consulta_compras:
consultar pedidos, compras pendentes, atrasos ou entregas.

analise_margem:
avaliar custo, lucro, margem, desconto ou rentabilidade.

analise_empresa:
diagnóstico amplo, riscos, prioridades ou direção da empresa.

consulta_produto:
consultar catálogo, produto, preço interno ou características.

consulta_fornecedor:
listar ou consultar dados cadastrais de fornecedores, sem
pedir uma recomendação de compra.

consulta_concorrente:
consultar concorrentes de forma geral. Preços explícitos em
Amazon ou Magazine Luiza são tratados por outra regra.

conversa:
pergunta geral que não depende de dados da empresa.

esclarecimento:
há intenção empresarial, mas falta produto ou informação
essencial e não existe contexto confirmado suficiente.

Regras:
1. Não responda à pergunta.
2. Não invente fatos empresariais.
3. Use o contexto confirmado para entender expressões como
   "ele", "esse produto", "desse aparelho" e "o mesmo item".
4. Escolha somente uma intenção.
5. O JSON não pode conter campos adicionais.
""".strip()

    mensagem_usuario = (
        f"{contexto}\n\n"
        f"Pergunta atual:\n{pergunta_limpa}\n\n"
        "Retorne o JSON."
    )

    modelo = criar_modelo().bind(
        response_format={
            "type": "json_object",
        },
        max_tokens=120,
    )

    resposta = modelo.invoke(
        [
            SystemMessage(
                content=instrucoes,
            ),
            HumanMessage(
                content=mensagem_usuario,
            ),
        ]
    )

    texto = _extrair_texto(
        resposta.content
    )

    try:
        dados = json.loads(
            texto
        )
    except json.JSONDecodeError as erro:
        raise ValueError(
            "O classificador retornou JSON inválido."
        ) from erro

    return _validar_resultado(
        dados
    )


__all__ = [
    "INTENCOES_SUPORTADAS",
    "ResultadoClassificacao",
    "classificar_intencao",
]
