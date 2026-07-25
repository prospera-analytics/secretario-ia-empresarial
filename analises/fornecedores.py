from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analises.estoque import analisar_cobertura_estoque
from database.models.compra import Compra
from database.models.fornecedor import Fornecedor
from database.models.produto import Produto


CENTAVOS = Decimal("0.01")
DUAS_CASAS = Decimal("0.01")


def _arredondar_moeda(
    valor: Decimal,
) -> Decimal:
    """Arredonda valores monetários para centavos."""

    return valor.quantize(
        CENTAVOS,
        rounding=ROUND_HALF_UP,
    )


def _arredondar_numero(
    valor: Decimal,
) -> Decimal:
    """Arredonda indicadores para duas casas decimais."""

    return valor.quantize(
        DUAS_CASAS,
        rounding=ROUND_HALF_UP,
    )


def calcular_compras_pendentes_produto(
    sessao: Session,
    produto_id: int,
    data_referencia: date | None = None,
) -> dict[str, Any]:
    """
    Calcula as compras pendentes de um produto.

    Nesta versão, somente o status 'pendente' representa mercadoria
    comprada que ainda não entrou no estoque.
    """

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    data_atual = data_referencia or date.today()

    consulta = (
        select(Compra)
        .where(
            Compra.produto_id == produto_id,
            Compra.status == "pendente",
        )
        .order_by(
            Compra.previsao_entrega.asc(),
            Compra.id.asc(),
        )
    )

    compras = list(
        sessao.scalars(consulta).all()
    )

    quantidade_total = sum(
        compra.quantidade
        for compra in compras
    )

    compras_formatadas = []

    for compra in compras:
        dias_ate_entrega = (
            compra.previsao_entrega - data_atual
        ).days

        compras_formatadas.append(
            {
                "compra_id": compra.id,
                "fornecedor_id": compra.fornecedor_id,
                "quantidade": compra.quantidade,
                "preco_unitario": float(
                    _arredondar_moeda(
                        Decimal(compra.preco_unitario)
                    )
                ),
                "data_compra": (
                    compra.data_compra.isoformat()
                ),
                "previsao_entrega": (
                    compra.previsao_entrega.isoformat()
                ),
                "dias_ate_entrega": dias_ate_entrega,
                "entrega_atrasada": dias_ate_entrega < 0,
                "status": compra.status,
            }
        )

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "quantidade_compras_pendentes": len(compras),
        "unidades_pendentes": quantidade_total,
        "compras": compras_formatadas,
    }


def buscar_ultima_compra_por_fornecedor(
    sessao: Session,
    produto_id: int,
    fornecedor_id: int,
) -> Compra | None:
    """
    Busca a compra mais recente do produto junto ao fornecedor.

    Compras canceladas não são consideradas.
    """

    consulta = (
        select(Compra)
        .where(
            Compra.produto_id == produto_id,
            Compra.fornecedor_id == fornecedor_id,
            Compra.status != "cancelada",
        )
        .order_by(
            Compra.data_compra.desc(),
            Compra.id.desc(),
        )
        .limit(1)
    )

    return sessao.scalar(consulta)


def listar_fornecedores_produto(
    sessao: Session,
    produto_id: int,
) -> list[dict[str, Any]]:
    """
    Lista fornecedores ativos que já venderam o produto.

    O preço exibido é histórico e corresponde à compra válida
    mais recente realizada com cada fornecedor.
    """

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    consulta_fornecedores = (
        select(Fornecedor)
        .join(
            Compra,
            Compra.fornecedor_id == Fornecedor.id,
        )
        .where(
            Compra.produto_id == produto_id,
            Compra.status != "cancelada",
            Fornecedor.ativo.is_(True),
        )
        .distinct()
        .order_by(
            Fornecedor.nome.asc()
        )
    )

    fornecedores = list(
        sessao.scalars(
            consulta_fornecedores
        ).all()
    )

    resultados = []

    for fornecedor in fornecedores:
        ultima_compra = buscar_ultima_compra_por_fornecedor(
            sessao=sessao,
            produto_id=produto_id,
            fornecedor_id=fornecedor.id,
        )

        if ultima_compra is None:
            continue

        resultados.append(
            {
                "fornecedor_id": fornecedor.id,
                "fornecedor_nome": fornecedor.nome,
                "cidade": fornecedor.cidade,
                "estado": fornecedor.estado,
                "prazo_entrega_dias": (
                    fornecedor.prazo_entrega_dias
                ),
                "preco_historico_referencia": float(
                    _arredondar_moeda(
                        Decimal(
                            ultima_compra.preco_unitario
                        )
                    )
                ),
                "data_preco_referencia": (
                    ultima_compra.data_compra.isoformat()
                ),
                "compra_referencia_id": (
                    ultima_compra.id
                ),
                "criterio_preco": (
                    "Preço da compra válida mais recente "
                    "realizada com o fornecedor"
                ),
            }
        )

    return resultados


def recomendar_fornecedor_produto(
    sessao: Session,
    produto_id: int,
    quantidade: int | None = None,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    data_referencia: date | None = None,
) -> dict[str, Any]:
    """
    Compara fornecedores por preço histórico e prazo de entrega.

    Também verifica se o estoque tende a acabar antes da entrega.

    A função não registra compras e não altera o estoque.
    """

    if quantidade is not None and quantidade <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    data_atual = data_referencia or date.today()

    analise_estoque = analisar_cobertura_estoque(
        sessao=sessao,
        produto_id=produto_id,
        dias_analise=dias_analise,
        dias_cobertura_desejada=(
            dias_cobertura_desejada
        ),
        data_referencia=data_atual,
    )

    if not analise_estoque.get(
        "possui_estoque_cadastrado",
        False,
    ):
        raise ValueError(
            "O produto não possui estoque cadastrado."
        )

    compras_pendentes = (
        calcular_compras_pendentes_produto(
            sessao=sessao,
            produto_id=produto_id,
            data_referencia=data_atual,
        )
    )

    fornecedores = listar_fornecedores_produto(
        sessao=sessao,
        produto_id=produto_id,
    )

    quantidade_sugerida = (
        quantidade
        if quantidade is not None
        else analise_estoque[
            "quantidade_reposicao_sugerida"
        ]
    )

    quantidade_atual = analise_estoque[
        "quantidade_atual"
    ]

    unidades_pendentes = compras_pendentes[
        "unidades_pendentes"
    ]

    estoque_projetado = (
        quantidade_atual
        + unidades_pendentes
    )

    media_diaria = Decimal(
        str(
            analise_estoque[
                "media_vendas_diaria"
            ]
        )
    )

    quantidade_necessaria_apos_pendencias = max(
        0,
        quantidade_sugerida - unidades_pendentes,
    )

    if not fornecedores:
        return {
            "produto_id": produto_id,
            "produto_nome": analise_estoque[
                "produto_nome"
            ],
            "possui_fornecedores_historicos": False,
            "quantidade_reposicao_original": (
                quantidade_sugerida
            ),
            "unidades_pendentes": unidades_pendentes,
            "quantidade_a_comprar_apos_pendencias": (
                quantidade_necessaria_apos_pendencias
            ),
            "mensagem": (
                "Não existem fornecedores ativos com histórico "
                "válido de compra para este produto."
            ),
        }

    comparacoes = []

    for fornecedor in fornecedores:
        prazo = fornecedor[
            "prazo_entrega_dias"
        ]

        preco_unitario = Decimal(
            str(
                fornecedor[
                    "preco_historico_referencia"
                ]
            )
        )

        consumo_ate_entrega = (
            media_diaria
            * Decimal(prazo)
        )

        estoque_estimado_na_entrega = (
            Decimal(estoque_projetado)
            - consumo_ate_entrega
        )

        risco_ruptura_antes_entrega = (
            media_diaria > 0
            and estoque_estimado_na_entrega < 0
        )

        if media_diaria > 0:
            dias_cobertura_projetada = (
                Decimal(estoque_projetado)
                / media_diaria
            )
        else:
            dias_cobertura_projetada = None

        custo_total_estimado = (
            preco_unitario
            * Decimal(
                quantidade_necessaria_apos_pendencias
            )
        )

        data_estimada_entrega = (
            data_atual
            + timedelta(days=prazo)
        )

        comparacoes.append(
            {
                **fornecedor,
                "quantidade_analisada": (
                    quantidade_necessaria_apos_pendencias
                ),
                "custo_total_estimado": float(
                    _arredondar_moeda(
                        custo_total_estimado
                    )
                ),
                "data_estimada_entrega": (
                    data_estimada_entrega.isoformat()
                ),
                "consumo_estimado_ate_entrega": float(
                    _arredondar_numero(
                        consumo_ate_entrega
                    )
                ),
                "estoque_estimado_na_entrega": float(
                    _arredondar_numero(
                        estoque_estimado_na_entrega
                    )
                ),
                "dias_cobertura_projetada": (
                    float(
                        _arredondar_numero(
                            dias_cobertura_projetada
                        )
                    )
                    if dias_cobertura_projetada
                    is not None
                    else None
                ),
                "risco_ruptura_antes_entrega": (
                    risco_ruptura_antes_entrega
                ),
            }
        )

    fornecedores_sem_risco = [
        item
        for item in comparacoes
        if not item[
            "risco_ruptura_antes_entrega"
        ]
    ]

    if fornecedores_sem_risco:
        melhor_fornecedor = min(
            fornecedores_sem_risco,
            key=lambda item: (
                item["custo_total_estimado"],
                item["prazo_entrega_dias"],
            ),
        )

        criterio_recomendacao = (
            "Menor custo estimado entre os fornecedores "
            "que conseguem entregar antes da ruptura."
        )

    else:
        melhor_fornecedor = min(
            comparacoes,
            key=lambda item: (
                item["prazo_entrega_dias"],
                item["custo_total_estimado"],
            ),
        )

        criterio_recomendacao = (
            "Nenhum fornecedor elimina o risco de ruptura; "
            "foi priorizado o menor prazo de entrega."
        )

    comparacoes.sort(
        key=lambda item: (
            item["risco_ruptura_antes_entrega"],
            item["custo_total_estimado"],
            item["prazo_entrega_dias"],
        )
    )

    compra_adicional_necessaria = (
        quantidade_necessaria_apos_pendencias > 0
    )

    return {
        "produto_id": produto_id,
        "produto_nome": analise_estoque[
            "produto_nome"
        ],
        "possui_fornecedores_historicos": True,
        "estoque_atual": quantidade_atual,
        "unidades_pendentes": unidades_pendentes,
        "estoque_projetado_com_pendencias": (
            estoque_projetado
        ),
        "quantidade_reposicao_original": (
            quantidade_sugerida
        ),
        "quantidade_a_comprar_apos_pendencias": (
            quantidade_necessaria_apos_pendencias
        ),
        "compra_adicional_necessaria": (
            compra_adicional_necessaria
        ),
        "media_vendas_diaria": float(
            _arredondar_numero(media_diaria)
        ),
        "melhor_fornecedor": melhor_fornecedor,
        "criterio_recomendacao": (
            criterio_recomendacao
        ),
        "observacao_preco": (
            "Os preços são históricos e precisam ser confirmados "
            "antes da realização de uma nova compra."
        ),
        "compras_pendentes": compras_pendentes[
            "compras"
        ],
        "comparacao_fornecedores": comparacoes,
    }