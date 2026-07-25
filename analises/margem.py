from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.compra import Compra
from database.models.produto import Produto


CENTAVOS = Decimal("0.01")
PERCENTUAL = Decimal("0.01")
CEM = Decimal("100")


def _decimal(
    valor: Decimal | float | int | str,
) -> Decimal:
    """Converte valores numéricos para Decimal."""

    return Decimal(str(valor))


def _arredondar_moeda(
    valor: Decimal,
) -> Decimal:
    """Arredonda um valor monetário para duas casas decimais."""

    return valor.quantize(
        CENTAVOS,
        rounding=ROUND_HALF_UP,
    )


def _arredondar_percentual(
    valor: Decimal,
) -> Decimal:
    """Arredonda um percentual para duas casas decimais."""

    return valor.quantize(
        PERCENTUAL,
        rounding=ROUND_HALF_UP,
    )


def buscar_ultima_compra_valida(
    sessao: Session,
    produto_id: int,
) -> Compra | None:
    """
    Busca a compra mais recente do produto que não foi cancelada.

    O preço unitário dessa compra será usado como referência de custo
    para a análise de margem.
    """

    consulta = (
        select(Compra)
        .where(
            Compra.produto_id == produto_id,
            Compra.status != "cancelada",
        )
        .order_by(
            Compra.data_compra.desc(),
            Compra.id.desc(),
        )
        .limit(1)
    )

    return sessao.scalar(consulta)


def analisar_margem_produto(
    sessao: Session,
    produto_id: int,
    desconto_percentual: Decimal | float | int | str = Decimal("0"),
    margem_minima_percentual: Decimal | float | int | str = Decimal("10"),
) -> dict[str, Any]:
    """
    Analisa margem, lucro e segurança de desconto de um produto.

    O custo de referência é o preço unitário da compra mais recente
    que não esteja cancelada.

    A função não altera o produto e não aplica descontos.
    """

    produto = sessao.get(
        Produto,
        produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    desconto = _decimal(desconto_percentual)
    margem_minima = _decimal(margem_minima_percentual)

    if desconto < 0 or desconto > 100:
        raise ValueError(
            "O desconto deve estar entre 0 e 100."
        )

    if margem_minima < 0 or margem_minima >= 100:
        raise ValueError(
            "A margem mínima deve estar entre 0 e menos de 100."
        )

    ultima_compra = buscar_ultima_compra_valida(
        sessao=sessao,
        produto_id=produto_id,
    )

    if ultima_compra is None:
        return {
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "marca": produto.marca,
            "armazenamento_gb": produto.armazenamento_gb,
            "preco_venda": float(
                _arredondar_moeda(
                    _decimal(produto.preco_venda)
                )
            ),
            "possui_custo_referencia": False,
            "criterio_custo": (
                "Compra mais recente não cancelada"
            ),
            "mensagem": (
                "Não existe uma compra válida para calcular "
                "a margem deste produto."
            ),
        }

    preco_venda = _decimal(
        produto.preco_venda
    )

    custo_unitario = _decimal(
        ultima_compra.preco_unitario
    )

    fator_desconto = (
        Decimal("1")
        - desconto / CEM
    )

    preco_com_desconto = (
        preco_venda * fator_desconto
    )

    lucro_unitario_atual = (
        preco_venda - custo_unitario
    )

    lucro_unitario_com_desconto = (
        preco_com_desconto - custo_unitario
    )

    margem_atual = (
        lucro_unitario_atual
        / preco_venda
        * CEM
    )

    margem_com_desconto = (
        lucro_unitario_com_desconto
        / preco_com_desconto
        * CEM
        if preco_com_desconto > 0
        else Decimal("-100")
    )

    desconto_maximo_sem_prejuizo = (
        (
            preco_venda - custo_unitario
        )
        / preco_venda
        * CEM
    )

    margem_minima_decimal = (
        margem_minima / CEM
    )

    preco_minimo_com_margem = (
        custo_unitario
        / (
            Decimal("1")
            - margem_minima_decimal
        )
    )

    desconto_maximo_com_margem = (
        (
            preco_venda
            - preco_minimo_com_margem
        )
        / preco_venda
        * CEM
    )

    desconto_maximo_com_margem = max(
        Decimal("0"),
        desconto_maximo_com_margem,
    )

    desconto_maximo_com_margem = min(
        CEM,
        desconto_maximo_com_margem,
    )

    vende_com_prejuizo = (
        lucro_unitario_com_desconto < 0
    )

    atende_margem_minima = (
        margem_com_desconto >= margem_minima
        and not vende_com_prejuizo
    )

    if vende_com_prejuizo:
        classificacao = "prejuizo"
        recomendacao = (
            "O desconto informado não deve ser aplicado, pois "
            "o preço final fica abaixo do custo de referência."
        )

    elif not atende_margem_minima:
        classificacao = "margem_baixa"
        recomendacao = (
            "O produto continua gerando lucro, mas a margem fica "
            "abaixo da margem mínima definida."
        )

    else:
        classificacao = "desconto_seguro"
        recomendacao = (
            "O desconto informado mantém o produto lucrativo e "
            "preserva a margem mínima definida."
        )

    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "marca": produto.marca,
        "armazenamento_gb": produto.armazenamento_gb,
        "produto_ativo": produto.ativo,
        "possui_custo_referencia": True,
        "criterio_custo": (
            "Preço unitário da compra mais recente "
            "que não esteja cancelada"
        ),
        "compra_referencia": {
            "compra_id": ultima_compra.id,
            "fornecedor_id": ultima_compra.fornecedor_id,
            "data_compra": (
                ultima_compra.data_compra.isoformat()
            ),
            "status": ultima_compra.status,
            "quantidade": ultima_compra.quantidade,
        },
        "preco_venda_atual": float(
            _arredondar_moeda(preco_venda)
        ),
        "custo_unitario_referencia": float(
            _arredondar_moeda(custo_unitario)
        ),
        "lucro_unitario_atual": float(
            _arredondar_moeda(
                lucro_unitario_atual
            )
        ),
        "margem_atual_percentual": float(
            _arredondar_percentual(
                margem_atual
            )
        ),
        "desconto_analisado_percentual": float(
            _arredondar_percentual(
                desconto
            )
        ),
        "preco_com_desconto": float(
            _arredondar_moeda(
                preco_com_desconto
            )
        ),
        "lucro_unitario_com_desconto": float(
            _arredondar_moeda(
                lucro_unitario_com_desconto
            )
        ),
        "margem_com_desconto_percentual": float(
            _arredondar_percentual(
                margem_com_desconto
            )
        ),
        "margem_minima_exigida_percentual": float(
            _arredondar_percentual(
                margem_minima
            )
        ),
        "preco_minimo_sem_prejuizo": float(
            _arredondar_moeda(
                custo_unitario
            )
        ),
        "desconto_maximo_sem_prejuizo_percentual": float(
            _arredondar_percentual(
                max(
                    Decimal("0"),
                    desconto_maximo_sem_prejuizo,
                )
            )
        ),
        "preco_minimo_com_margem_exigida": float(
            _arredondar_moeda(
                preco_minimo_com_margem
            )
        ),
        "desconto_maximo_com_margem_exigida_percentual": float(
            _arredondar_percentual(
                desconto_maximo_com_margem
            )
        ),
        "vende_com_prejuizo": vende_com_prejuizo,
        "atende_margem_minima": atende_margem_minima,
        "classificacao": classificacao,
        "recomendacao": recomendacao,
    }


def listar_analises_margem(
    sessao: Session,
    desconto_percentual: Decimal | float | int | str = Decimal("0"),
    margem_minima_percentual: Decimal | float | int | str = Decimal("10"),
    apenas_ativos: bool = True,
) -> list[dict[str, Any]]:
    """
    Analisa a margem de todos os produtos.

    Por padrão, considera apenas produtos ativos.
    """

    consulta = select(Produto).order_by(
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
        analisar_margem_produto(
            sessao=sessao,
            produto_id=produto.id,
            desconto_percentual=desconto_percentual,
            margem_minima_percentual=(
                margem_minima_percentual
            ),
        )
        for produto in produtos
    ]

    ordem_classificacao = {
        "prejuizo": 0,
        "margem_baixa": 1,
        "desconto_seguro": 2,
    }

    resultados.sort(
        key=lambda item: (
            ordem_classificacao.get(
                item.get("classificacao", ""),
                3,
            ),
            item["produto_nome"],
        )
    )

    return resultados