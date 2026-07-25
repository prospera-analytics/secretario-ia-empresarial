from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.estoque import Estoque
from database.models.produto import Produto
from database.models.venda import Venda


DUAS_CASAS = Decimal("0.01")


def _arredondar(
    valor: Decimal,
) -> Decimal:
    """Arredonda um valor para duas casas decimais."""

    return valor.quantize(
        DUAS_CASAS,
        rounding=ROUND_HALF_UP,
    )


def calcular_vendas_periodo(
    sessao: Session,
    produto_id: int,
    dias_analise: int = 30,
    data_referencia: date | None = None,
) -> dict[str, Any]:
    """
    Calcula as vendas de um produto em determinado período.

    A média diária usa todos os dias do período, inclusive os dias
    em que nenhuma unidade foi vendida.
    """

    if dias_analise <= 0:
        raise ValueError(
            "O período de análise deve ser maior que zero."
        )

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    data_final = data_referencia or date.today()

    data_inicial = (
        data_final
        - timedelta(days=dias_analise - 1)
    )

    consulta = select(
        func.coalesce(
            func.sum(Venda.quantidade),
            0,
        )
    ).where(
        Venda.produto_id == produto_id,
        Venda.data_venda >= data_inicial,
        Venda.data_venda <= data_final,
    )

    unidades_vendidas = int(
        sessao.scalar(consulta) or 0
    )

    media_diaria = (
        Decimal(unidades_vendidas)
        / Decimal(dias_analise)
    )

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "data_inicial": data_inicial.isoformat(),
        "data_final": data_final.isoformat(),
        "dias_analisados": dias_analise,
        "unidades_vendidas": unidades_vendidas,
        "media_vendas_diaria": float(
            _arredondar(media_diaria)
        ),
    }


def analisar_cobertura_estoque(
    sessao: Session,
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    data_referencia: date | None = None,
) -> dict[str, Any]:
    """
    Analisa velocidade de vendas, cobertura e necessidade de reposição.

    A quantidade sugerida busca alcançar a cobertura desejada,
    preservando também o estoque mínimo configurado.

    Esta função não cria compras e não altera o estoque.
    """

    if dias_cobertura_desejada <= 0:
        raise ValueError(
            "A cobertura desejada deve ser maior que zero."
        )

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    consulta_estoque = select(
        Estoque
    ).where(
        Estoque.produto_id == produto_id
    )

    estoque = sessao.scalar(
        consulta_estoque
    )

    if estoque is None:
        return {
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "produto_ativo": produto.ativo,
            "possui_estoque_cadastrado": False,
            "nivel_alerta": "critico",
            "classificacao": "estoque_nao_cadastrado",
            "mensagem": (
                "O produto não possui um registro de estoque."
            ),
        }

    vendas = calcular_vendas_periodo(
        sessao=sessao,
        produto_id=produto_id,
        dias_analise=dias_analise,
        data_referencia=data_referencia,
    )

    quantidade_atual = estoque.quantidade_atual
    estoque_minimo = estoque.estoque_minimo

    media_diaria = Decimal(
        str(vendas["media_vendas_diaria"])
    )

    abaixo_do_minimo = (
        quantidade_atual <= estoque_minimo
    )

    if media_diaria > 0:
        dias_cobertura = (
            Decimal(quantidade_atual)
            / media_diaria
        )

        consumo_cobertura_desejada = (
            media_diaria
            * Decimal(dias_cobertura_desejada)
        )

        estoque_alvo = max(
            Decimal(estoque_minimo),
            consumo_cobertura_desejada,
        )

        quantidade_reposicao = max(
            Decimal("0"),
            estoque_alvo
            - Decimal(quantidade_atual),
        )

        quantidade_reposicao_inteira = int(
    quantidade_reposicao.to_integral_value(
        rounding=ROUND_CEILING
    )
)

    else:
        dias_cobertura = None

        quantidade_reposicao_inteira = max(
            0,
            estoque_minimo - quantidade_atual,
        )

    sem_estoque = quantidade_atual == 0

    if sem_estoque and media_diaria > 0:
        nivel_alerta = "critico"
        classificacao = "ruptura_estoque"
        recomendacao = (
            "O produto está sem estoque e teve vendas no período. "
            "A reposição deve ser tratada como urgente."
        )

    elif media_diaria > 0 and dias_cobertura is not None:
        if dias_cobertura <= Decimal("7"):
            nivel_alerta = "critico"
            classificacao = "cobertura_critica"
            recomendacao = (
                "A cobertura estimada é de até 7 dias. "
                "Recomenda-se iniciar a reposição imediatamente."
            )

        elif dias_cobertura <= Decimal("14"):
            nivel_alerta = "atencao"
            classificacao = "cobertura_baixa"
            recomendacao = (
                "A cobertura estimada é de até 14 dias. "
                "Planeje uma nova compra antes do risco de ruptura."
            )

        elif abaixo_do_minimo:
            nivel_alerta = "atencao"
            classificacao = "abaixo_estoque_minimo"
            recomendacao = (
                "O estoque está no nível mínimo ou abaixo dele."
            )

        else:
            nivel_alerta = "normal"
            classificacao = "estoque_adequado"
            recomendacao = (
                "O estoque possui cobertura adequada com base "
                "no período analisado."
            )

    elif abaixo_do_minimo:
        nivel_alerta = "atencao"
        classificacao = "abaixo_minimo_sem_vendas_recentes"
        recomendacao = (
            "O estoque está no nível mínimo ou abaixo dele, mas "
            "não houve vendas no período analisado."
        )

    else:
        nivel_alerta = "informativo"
        classificacao = "sem_vendas_recentes"
        recomendacao = (
            "Não houve vendas no período. Não há evidência de "
            "urgência para reposição baseada na demanda recente."
        )

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "produto_ativo": produto.ativo,
        "possui_estoque_cadastrado": True,
        "quantidade_atual": quantidade_atual,
        "estoque_minimo": estoque_minimo,
        "abaixo_ou_igual_estoque_minimo": abaixo_do_minimo,
        "periodo_analise": {
            "data_inicial": vendas["data_inicial"],
            "data_final": vendas["data_final"],
            "dias": vendas["dias_analisados"],
        },
        "unidades_vendidas_periodo": (
            vendas["unidades_vendidas"]
        ),
        "media_vendas_diaria": (
            vendas["media_vendas_diaria"]
        ),
        "dias_cobertura_estimados": (
            float(_arredondar(dias_cobertura))
            if dias_cobertura is not None
            else None
        ),
        "dias_cobertura_desejada": (
            dias_cobertura_desejada
        ),
        "quantidade_reposicao_sugerida": (
            quantidade_reposicao_inteira
        ),
        "nivel_alerta": nivel_alerta,
        "classificacao": classificacao,
        "recomendacao": recomendacao,
    }


def listar_analises_estoque(
    sessao: Session,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    apenas_ativos: bool = True,
    apenas_com_alerta: bool = False,
    data_referencia: date | None = None,
) -> list[dict[str, Any]]:
    """
    Analisa o estoque de todos os produtos.

    Os resultados são ordenados do nível mais urgente para o normal.
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

    produtos = sessao.scalars(
        consulta
    ).all()

    resultados = [
        analisar_cobertura_estoque(
            sessao=sessao,
            produto_id=produto.id,
            dias_analise=dias_analise,
            dias_cobertura_desejada=(
                dias_cobertura_desejada
            ),
            data_referencia=data_referencia,
        )
        for produto in produtos
    ]

    if apenas_com_alerta:
        resultados = [
            item
            for item in resultados
            if item["nivel_alerta"]
            in {"critico", "atencao"}
        ]

    ordem_nivel = {
        "critico": 0,
        "atencao": 1,
        "informativo": 2,
        "normal": 3,
    }

    resultados.sort(
        key=lambda item: (
            ordem_nivel.get(
                item["nivel_alerta"],
                4,
            ),
            item["produto_nome"],
        )
    )

    return resultados