from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analises.estoque import analisar_cobertura_estoque
from analises.fornecedores import (
    calcular_compras_pendentes_produto,
    recomendar_fornecedor_produto,
)
from analises.margem import analisar_margem_produto
from crud.concorrente import buscar_menor_preco_concorrente
from database.models.produto import Produto


DUAS_CASAS = Decimal("0.01")
CEM = Decimal("100")


ORDEM_SEVERIDADE = {
    "critico": 0,
    "atencao": 1,
    "informativo": 2,
}


def _decimal(
    valor: Decimal | float | int | str,
) -> Decimal:
    """Converte um valor numérico para Decimal."""

    return Decimal(str(valor))


def _arredondar(
    valor: Decimal,
) -> Decimal:
    """Arredonda um indicador para duas casas decimais."""

    return valor.quantize(
        DUAS_CASAS,
        rounding=ROUND_HALF_UP,
    )


def _criar_alerta(
    *,
    tipo: str,
    severidade: str,
    titulo: str,
    mensagem: str,
    recomendacao: str,
    produto: Produto,
    dados: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cria a estrutura padronizada de um alerta empresarial."""

    return {
        "tipo": tipo,
        "severidade": severidade,
        "titulo": titulo,
        "mensagem": mensagem,
        "recomendacao": recomendacao,
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "dados": dados or {},
    }


def gerar_alertas_produto(
    sessao: Session,
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: Decimal | float | int | str = Decimal("10"),
    diferenca_concorrente_alerta_percentual: Decimal | float | int | str = Decimal("3"),
    incluir_informativos: bool = True,
) -> list[dict[str, Any]]:
    """
    Gera alertas empresariais para um produto.

    A função é somente leitura e não altera preços, estoque,
    compras ou campanhas.
    """

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    margem_minima = _decimal(
        margem_minima_percentual
    )

    diferenca_minima_concorrente = _decimal(
        diferenca_concorrente_alerta_percentual
    )

    if margem_minima < 0 or margem_minima >= 100:
        raise ValueError(
            "A margem mínima deve estar entre 0 e menos de 100."
        )

    if (
        diferenca_minima_concorrente < 0
        or diferenca_minima_concorrente > 100
    ):
        raise ValueError(
            "A diferença mínima do concorrente deve estar "
            "entre 0 e 100."
        )

    alertas: list[dict[str, Any]] = []

    # ==========================================================
    # ALERTAS DE ESTOQUE
    # ==========================================================

    analise_estoque = analisar_cobertura_estoque(
        sessao=sessao,
        produto_id=produto_id,
        dias_analise=dias_analise,
        dias_cobertura_desejada=(
            dias_cobertura_desejada
        ),
    )

    nivel_estoque = analise_estoque[
        "nivel_alerta"
    ]

    classificacao_estoque = analise_estoque[
        "classificacao"
    ]

    if nivel_estoque in {
        "critico",
        "atencao",
    }:
        dias_cobertura = analise_estoque.get(
            "dias_cobertura_estimados"
        )

        if dias_cobertura is None:
            texto_cobertura = (
                "Não foi possível estimar os dias de cobertura."
            )
        else:
            texto_cobertura = (
                f"A cobertura estimada é de "
                f"{dias_cobertura:.2f} dias."
            )

        alertas.append(
            _criar_alerta(
                tipo="estoque",
                severidade=nivel_estoque,
                titulo="Risco relacionado ao estoque",
                mensagem=(
                    f"{texto_cobertura} "
                    f"O estoque atual é de "
                    f"{analise_estoque.get('quantidade_atual', 0)} "
                    f"unidades e o estoque mínimo é de "
                    f"{analise_estoque.get('estoque_minimo', 0)}."
                ),
                recomendacao=(
                    analise_estoque["recomendacao"]
                ),
                produto=produto,
                dados={
                    "classificacao": (
                        classificacao_estoque
                    ),
                    "quantidade_atual": (
                        analise_estoque.get(
                            "quantidade_atual"
                        )
                    ),
                    "estoque_minimo": (
                        analise_estoque.get(
                            "estoque_minimo"
                        )
                    ),
                    "dias_cobertura_estimados": (
                        dias_cobertura
                    ),
                    "quantidade_reposicao_sugerida": (
                        analise_estoque.get(
                            "quantidade_reposicao_sugerida"
                        )
                    ),
                },
            )
        )

    elif (
        incluir_informativos
        and nivel_estoque == "informativo"
    ):
        alertas.append(
            _criar_alerta(
                tipo="estoque",
                severidade="informativo",
                titulo="Produto sem vendas recentes",
                mensagem=(
                    f"Não houve vendas do produto nos últimos "
                    f"{dias_analise} dias."
                ),
                recomendacao=(
                    "Evite uma nova reposição baseada apenas no "
                    "estoque mínimo. Avalie a baixa demanda antes "
                    "de imobilizar mais capital."
                ),
                produto=produto,
                dados={
                    "quantidade_atual": (
                        analise_estoque.get(
                            "quantidade_atual"
                        )
                    ),
                    "estoque_minimo": (
                        analise_estoque.get(
                            "estoque_minimo"
                        )
                    ),
                    "unidades_vendidas_periodo": (
                        analise_estoque.get(
                            "unidades_vendidas_periodo"
                        )
                    ),
                },
            )
        )

    # ==========================================================
    # COMPRAS PENDENTES ATRASADAS
    # ==========================================================

    compras_pendentes = (
        calcular_compras_pendentes_produto(
            sessao=sessao,
            produto_id=produto_id,
        )
    )

    compras_atrasadas = [
        compra
        for compra in compras_pendentes["compras"]
        if compra["entrega_atrasada"]
    ]

    if compras_atrasadas:
        unidades_atrasadas = sum(
            compra["quantidade"]
            for compra in compras_atrasadas
        )

        alertas.append(
            _criar_alerta(
                tipo="compra_atrasada",
                severidade="critico",
                titulo="Compra pendente com entrega atrasada",
                mensagem=(
                    f"Existem {len(compras_atrasadas)} compras "
                    f"pendentes atrasadas, totalizando "
                    f"{unidades_atrasadas} unidades."
                ),
                recomendacao=(
                    "Entre em contato com os fornecedores e não "
                    "considere essas unidades como disponíveis "
                    "até confirmar uma nova previsão de entrega."
                ),
                produto=produto,
                dados={
                    "quantidade_compras_atrasadas": (
                        len(compras_atrasadas)
                    ),
                    "unidades_atrasadas": (
                        unidades_atrasadas
                    ),
                    "compras_atrasadas": (
                        compras_atrasadas
                    ),
                },
            )
        )

    # ==========================================================
    # ALERTAS DE MARGEM
    # ==========================================================

    analise_margem = analisar_margem_produto(
        sessao=sessao,
        produto_id=produto_id,
        desconto_percentual=0,
        margem_minima_percentual=margem_minima,
    )

    possui_custo = analise_margem[
        "possui_custo_referencia"
    ]

    if not possui_custo:
        alertas.append(
            _criar_alerta(
                tipo="custo_desconhecido",
                severidade="atencao",
                titulo="Custo de referência indisponível",
                mensagem=(
                    "Não existe uma compra válida para calcular "
                    "o custo e a margem do produto."
                ),
                recomendacao=(
                    "Registre ou confirme uma compra válida antes "
                    "de recomendar descontos ou avaliar a "
                    "rentabilidade deste produto."
                ),
                produto=produto,
            )
        )

    else:
        margem_atual = _decimal(
            analise_margem[
                "margem_atual_percentual"
            ]
        )

        lucro_unitario = _decimal(
            analise_margem[
                "lucro_unitario_atual"
            ]
        )

        if lucro_unitario <= 0:
            alertas.append(
                _criar_alerta(
                    tipo="margem",
                    severidade="critico",
                    titulo="Produto vendido sem lucro",
                    mensagem=(
                        f"O lucro unitário estimado é de "
                        f"R$ {lucro_unitario:.2f} e a margem "
                        f"atual é de {margem_atual:.2f}%."
                    ),
                    recomendacao=(
                        "Revise imediatamente o preço de venda ou "
                        "o custo de aquisição. Não aplique novos "
                        "descontos enquanto a situação persistir."
                    ),
                    produto=produto,
                    dados={
                        "preco_venda_atual": (
                            analise_margem[
                                "preco_venda_atual"
                            ]
                        ),
                        "custo_unitario_referencia": (
                            analise_margem[
                                "custo_unitario_referencia"
                            ]
                        ),
                        "lucro_unitario_atual": float(
                            lucro_unitario
                        ),
                        "margem_atual_percentual": float(
                            margem_atual
                        ),
                    },
                )
            )

        elif margem_atual < margem_minima:
            alertas.append(
                _criar_alerta(
                    tipo="margem",
                    severidade="atencao",
                    titulo="Margem abaixo do mínimo",
                    mensagem=(
                        f"A margem atual é de "
                        f"{margem_atual:.2f}%, abaixo do mínimo "
                        f"definido de {margem_minima:.2f}%."
                    ),
                    recomendacao=(
                        "Evite descontos adicionais e avalie "
                        "aumentar o preço ou negociar um custo "
                        "menor com o fornecedor."
                    ),
                    produto=produto,
                    dados={
                        "margem_atual_percentual": float(
                            margem_atual
                        ),
                        "margem_minima_percentual": float(
                            margem_minima
                        ),
                        "lucro_unitario_atual": float(
                            lucro_unitario
                        ),
                    },
                )
            )

    # ==========================================================
    # ALERTAS DE CONCORRÊNCIA
    # ==========================================================

    menor_preco = buscar_menor_preco_concorrente(
        sessao=sessao,
        produto_id=produto_id,
        apenas_correspondencia_exata=True,
    )

    if menor_preco is not None:
        preco_empresa = _decimal(
            produto.preco_venda
        )

        preco_concorrente = _decimal(
            menor_preco.preco
        )

        if preco_concorrente < preco_empresa:
            diferenca_valor = (
                preco_empresa - preco_concorrente
            )

            diferenca_percentual = (
                diferenca_valor
                / preco_empresa
                * CEM
            )

            if (
                diferenca_percentual
                >= diferenca_minima_concorrente
            ):
                dados_concorrencia: dict[str, Any] = {
                    "preco_empresa": float(
                        _arredondar(preco_empresa)
                    ),
                    "preco_concorrente": float(
                        _arredondar(preco_concorrente)
                    ),
                    "diferenca_valor": float(
                        _arredondar(diferenca_valor)
                    ),
                    "diferenca_percentual": float(
                        _arredondar(
                            diferenca_percentual
                        )
                    ),
                    "concorrente_id": (
                        menor_preco.concorrente_id
                    ),
                    "url": menor_preco.url,
                }

                if possui_custo:
                    custo = _decimal(
                        analise_margem[
                            "custo_unitario_referencia"
                        ]
                    )

                    lucro_ao_igualar = (
                        preco_concorrente - custo
                    )

                    margem_ao_igualar = (
                        lucro_ao_igualar
                        / preco_concorrente
                        * CEM
                    )

                    pode_igualar_sem_prejuizo = (
                        lucro_ao_igualar >= 0
                    )

                    preserva_margem_minima = (
                        margem_ao_igualar
                        >= margem_minima
                    )

                    dados_concorrencia.update(
                        {
                            "lucro_unitario_ao_igualar": float(
                                _arredondar(
                                    lucro_ao_igualar
                                )
                            ),
                            "margem_ao_igualar_percentual": float(
                                _arredondar(
                                    margem_ao_igualar
                                )
                            ),
                            "pode_igualar_sem_prejuizo": (
                                pode_igualar_sem_prejuizo
                            ),
                            "preserva_margem_minima": (
                                preserva_margem_minima
                            ),
                        }
                    )

                    if not pode_igualar_sem_prejuizo:
                        severidade = "critico"
                        recomendacao = (
                            "Não iguale o preço do concorrente, "
                            "pois isso produziria prejuízo. Avalie "
                            "negociar o custo, oferecer benefícios "
                            "não financeiros ou reposicionar o "
                            "produto."
                        )

                    elif not preserva_margem_minima:
                        severidade = "atencao"
                        recomendacao = (
                            "É possível igualar o concorrente sem "
                            "prejuízo, mas a margem ficaria abaixo "
                            "do mínimo. Avalie se a redução é "
                            "estrategicamente justificável."
                        )

                    else:
                        severidade = "atencao"
                        recomendacao = (
                            "Existe espaço financeiro para igualar "
                            "o concorrente mantendo a margem mínima, "
                            "mas a mudança não deve ser automática."
                        )

                else:
                    severidade = "atencao"
                    recomendacao = (
                        "Confirme o custo do produto antes de "
                        "avaliar uma redução de preço."
                    )

                alertas.append(
                    _criar_alerta(
                        tipo="concorrencia",
                        severidade=severidade,
                        titulo="Concorrente com preço menor",
                        mensagem=(
                            f"O preço concorrente de "
                            f"R$ {preco_concorrente:.2f} está "
                            f"{diferenca_percentual:.2f}% abaixo "
                            f"do preço interno de "
                            f"R$ {preco_empresa:.2f}."
                        ),
                        recomendacao=recomendacao,
                        produto=produto,
                        dados=dados_concorrencia,
                    )
                )

    # ==========================================================
    # REPOSIÇÃO SEM FORNECEDOR
    # ==========================================================

    quantidade_reposicao = (
        analise_estoque.get(
            "quantidade_reposicao_sugerida",
            0,
        )
    )

    if quantidade_reposicao > 0:
        recomendacao_fornecedor = (
            recomendar_fornecedor_produto(
                sessao=sessao,
                produto_id=produto_id,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
            )
        )

        possui_fornecedores = (
            recomendacao_fornecedor.get(
                "possui_fornecedores_historicos",
                False,
            )
        )

        if not possui_fornecedores:
            alertas.append(
                _criar_alerta(
                    tipo="fornecedor",
                    severidade="critico",
                    titulo="Reposição sem fornecedor disponível",
                    mensagem=(
                        f"A análise recomenda repor "
                        f"{quantidade_reposicao} unidades, mas não "
                        "há fornecedor ativo com histórico válido "
                        "para este produto."
                    ),
                    recomendacao=(
                        "Cadastre ou reative um fornecedor e "
                        "obtenha uma cotação antes que o estoque "
                        "seja esgotado."
                    ),
                    produto=produto,
                    dados={
                        "quantidade_reposicao_sugerida": (
                            quantidade_reposicao
                        ),
                    },
                )
            )

    alertas.sort(
        key=lambda alerta: (
            ORDEM_SEVERIDADE.get(
                alerta["severidade"],
                3,
            ),
            alerta["tipo"],
        )
    )

    return alertas


def gerar_alertas_empresariais(
    sessao: Session,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: Decimal | float | int | str = Decimal("10"),
    diferenca_concorrente_alerta_percentual: Decimal | float | int | str = Decimal("3"),
    apenas_ativos: bool = True,
    incluir_informativos: bool = True,
) -> dict[str, Any]:
    """
    Gera um painel consolidado de alertas para todos os produtos.

    Erros isolados são registrados no resultado sem interromper
    a análise dos demais produtos.
    """

    consulta = select(
        Produto
    ).order_by(
        Produto.nome.asc()
    )

    if apenas_ativos:
        consulta = consulta.where(
            Produto.ativo.is_(True)
        )

    produtos = list(
        sessao.scalars(consulta).all()
    )

    alertas: list[dict[str, Any]] = []
    erros: list[dict[str, Any]] = []

    for produto in produtos:
        try:
            alertas_produto = gerar_alertas_produto(
                sessao=sessao,
                produto_id=produto.id,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
                diferenca_concorrente_alerta_percentual=(
                    diferenca_concorrente_alerta_percentual
                ),
                incluir_informativos=(
                    incluir_informativos
                ),
            )

            alertas.extend(
                alertas_produto
            )

        except Exception as erro:
            erros.append(
                {
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "erro": str(erro),
                }
            )

    alertas.sort(
        key=lambda alerta: (
            ORDEM_SEVERIDADE.get(
                alerta["severidade"],
                3,
            ),
            alerta["produto_nome"],
            alerta["tipo"],
        )
    )

    resumo = {
        "critico": sum(
            alerta["severidade"] == "critico"
            for alerta in alertas
        ),
        "atencao": sum(
            alerta["severidade"] == "atencao"
            for alerta in alertas
        ),
        "informativo": sum(
            alerta["severidade"] == "informativo"
            for alerta in alertas
        ),
    }

    produtos_com_alerta = len(
        {
            alerta["produto_id"]
            for alerta in alertas
        }
    )

    return {
        "quantidade_produtos_analisados": len(
            produtos
        ),
        "quantidade_produtos_com_alerta": (
            produtos_com_alerta
        ),
        "quantidade_alertas": len(alertas),
        "resumo": resumo,
        "parametros": {
            "dias_analise": dias_analise,
            "dias_cobertura_desejada": (
                dias_cobertura_desejada
            ),
            "margem_minima_percentual": float(
                _decimal(
                    margem_minima_percentual
                )
            ),
            "diferenca_concorrente_alerta_percentual": float(
                _decimal(
                    diferenca_concorrente_alerta_percentual
                )
            ),
            "apenas_ativos": apenas_ativos,
            "incluir_informativos": (
                incluir_informativos
            ),
        },
        "alertas": alertas,
        "erros": erros,
    }