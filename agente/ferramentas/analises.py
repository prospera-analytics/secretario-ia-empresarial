from typing import Any

from langchain_core.tools import tool

from analises.margem import (
    analisar_margem_produto,
    listar_analises_margem,
)
from database.conexao import SessionLocal

from analises.estoque import (
    analisar_cobertura_estoque,
    listar_analises_estoque,
)

from analises.fornecedores import (
    recomendar_fornecedor_produto,
)

from analises.alertas import (
    gerar_alertas_empresariais,
    gerar_alertas_produto,
)

from sqlalchemy import func, select

from database.models import Produto

def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza erros das ferramentas analíticas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


def _resolver_produto_id(
    sessao,
    produto_id: int | str,
) -> int:
    """
    Resolve um produto informado por ID numérico ou nome.

    Evita falhas quando o modelo envia o nome do produto no campo
    produto_id.
    """

    if isinstance(produto_id, int):
        if produto_id <= 0:
            raise ValueError(
                "O produto_id deve ser maior que zero."
            )

        produto = sessao.get(
            Produto,
            produto_id,
        )

        if produto is None:
            raise ValueError(
                f"Produto com ID {produto_id} não encontrado."
            )

        return produto.id

    if not isinstance(produto_id, str):
        raise TypeError(
            "O produto deve ser informado por ID ou nome."
        )

    termo = produto_id.strip()

    if not termo:
        raise ValueError(
            "O nome do produto não pode estar vazio."
        )

    if termo.isdigit():
        return _resolver_produto_id(
            sessao=sessao,
            produto_id=int(termo),
        )

    produto_exato = sessao.scalar(
        select(Produto)
        .where(
            func.lower(Produto.nome)
            == termo.casefold()
        )
        .where(
            Produto.ativo.is_(True)
        )
        .limit(1)
    )

    if produto_exato is not None:
        return produto_exato.id

    produtos = list(
        sessao.scalars(
            select(Produto)
            .where(
                Produto.nome.ilike(
                    f"%{termo}%"
                )
            )
            .where(
                Produto.ativo.is_(True)
            )
            .order_by(
                Produto.nome
            )
            .limit(5)
        ).all()
    )

    if not produtos:
        raise ValueError(
            f"Nenhum produto encontrado para: {termo}."
        )

    if len(produtos) > 1:
        nomes = ", ".join(
            produto.nome
            for produto in produtos
        )

        raise ValueError(
            "A identificação do produto ficou ambígua. "
            f"Resultados encontrados: {nomes}."
        )

    return produtos[0].id


def _converter_inteiro_positivo(
    valor: int | str,
    nome: str,
) -> int:
    """
    Converte um valor numérico ou uma string para inteiro positivo.
    """

    try:
        convertido = int(
            str(valor).strip()
        )

    except (
        TypeError,
        ValueError,
    ) as erro:
        raise ValueError(
            f"{nome} precisa ser um número inteiro."
        ) from erro

    if convertido <= 0:
        raise ValueError(
            f"{nome} precisa ser maior que zero."
        )

    return convertido

@tool
def analisar_desconto_produto(
    produto_id: int,
    desconto_percentual: float = 0,
    margem_minima_percentual: float = 10,
) -> dict[str, Any]:
    """
    Analisa se um desconto é financeiramente seguro para um produto.

    Calcula preço final, lucro unitário, margem resultante, desconto
    máximo sem prejuízo e desconto máximo preservando a margem mínima.

    Esta ferramenta apenas analisa. Ela não altera o preço do produto
    e não aplica o desconto.
    """

    try:
        with SessionLocal() as sessao:
            analise = analisar_margem_produto(
                sessao=sessao,
                produto_id=produto_id,
                desconto_percentual=desconto_percentual,
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def analisar_descontos_todos_produtos(
    desconto_percentual: float = 0,
    margem_minima_percentual: float = 10,
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Analisa o impacto de um desconto em todos os produtos.

    Identifica produtos que ficariam com prejuízo, margem baixa ou
    desconto financeiramente seguro.

    Esta ferramenta não altera preços nem aplica descontos.
    """

    try:
        with SessionLocal() as sessao:
            analises = listar_analises_margem(
                sessao=sessao,
                desconto_percentual=desconto_percentual,
                margem_minima_percentual=(
                    margem_minima_percentual
                ),
                apenas_ativos=apenas_ativos,
            )

            resumo = {
                "prejuizo": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "prejuizo"
                ),
                "margem_baixa": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "margem_baixa"
                ),
                "desconto_seguro": sum(
                    1
                    for item in analises
                    if item.get("classificacao")
                    == "desconto_seguro"
                ),
                "sem_custo_referencia": sum(
                    1
                    for item in analises
                    if not item.get(
                        "possui_custo_referencia",
                        False,
                    )
                ),
            }

            return {
                "sucesso": True,
                "desconto_analisado_percentual": (
                    desconto_percentual
                ),
                "margem_minima_percentual": (
                    margem_minima_percentual
                ),
                "quantidade_produtos": len(
                    analises
                ),
                "resumo": resumo,
                "analises": analises,
            }

    except Exception as erro:
        return _resposta_erro(erro)

@tool
def analisar_risco_estoque_produto(
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
) -> dict[str, Any]:
    """
    Analisa velocidade de vendas, dias de cobertura e risco de
    ruptura de estoque para um produto.

    Também sugere uma quantidade de reposição, mas não cria compras
    e não altera o estoque.
    """

    try:
        with SessionLocal() as sessao:
            analise = analisar_cobertura_estoque(
                sessao=sessao,
                produto_id=produto_id,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_alertas_estoque(
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    apenas_ativos: bool = True,
    apenas_com_alerta: bool = True,
) -> dict[str, Any]:
    """
    Analisa o estoque de todos os produtos e lista riscos de ruptura,
    cobertura baixa, estoque mínimo e produtos sem vendas recentes.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            analises = listar_analises_estoque(
                sessao=sessao,
                dias_analise=dias_analise,
                dias_cobertura_desejada=(
                    dias_cobertura_desejada
                ),
                apenas_ativos=apenas_ativos,
                apenas_com_alerta=apenas_com_alerta,
            )

            resumo = {
                "critico": sum(
                    item["nivel_alerta"] == "critico"
                    for item in analises
                ),
                "atencao": sum(
                    item["nivel_alerta"] == "atencao"
                    for item in analises
                ),
                "informativo": sum(
                    item["nivel_alerta"] == "informativo"
                    for item in analises
                ),
                "normal": sum(
                    item["nivel_alerta"] == "normal"
                    for item in analises
                ),
            }

            return {
                "sucesso": True,
                "quantidade": len(analises),
                "dias_analise": dias_analise,
                "dias_cobertura_desejada": (
                    dias_cobertura_desejada
                ),
                "apenas_com_alerta": apenas_com_alerta,
                "resumo": resumo,
                "analises": analises,
            }

    except Exception as erro:
        return _resposta_erro(erro)
    
@tool
def recomendar_fornecedor_para_reposicao(
    produto_id: int | str,
    quantidade: int | str | None = None,
    dias_analise: int | str = 30,
    dias_cobertura_desejada: int | str = 30,
) -> dict[str, Any]:
    """
    Recomenda um fornecedor para repor um produto.

    O produto pode ser informado por ID numérico ou pelo nome.
    Compara preço histórico, prazo, risco de ruptura e compras
    pendentes.
    """

    try:
        with SessionLocal() as sessao:
            produto_id_resolvido = _resolver_produto_id(
                sessao=sessao,
                produto_id=produto_id,
            )

            dias_analise_resolvido = (
                _converter_inteiro_positivo(
                    dias_analise,
                    "dias_analise",
                )
            )

            dias_cobertura_resolvido = (
                _converter_inteiro_positivo(
                    dias_cobertura_desejada,
                    "dias_cobertura_desejada",
                )
            )

            quantidade_resolvida = None

            if quantidade is not None:
                quantidade_resolvida = (
                    _converter_inteiro_positivo(
                        quantidade,
                        "quantidade",
                    )
                )

            analise = recomendar_fornecedor_produto(
                sessao=sessao,
                produto_id=produto_id_resolvido,
                quantidade=quantidade_resolvida,
                dias_analise=dias_analise_resolvido,
                dias_cobertura_desejada=(
                    dias_cobertura_resolvido
                ),
            )

            return {
                "sucesso": True,
                "analise": analise,
            }

    except Exception as erro:
        return _resposta_erro(
            erro
        )


@tool
def analisar_prioridades_reposicao_catalogo(
    dias_analise: int | str = 30,
    dias_cobertura_desejada: int | str = 30,
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Analisa todos os produtos e define a prioridade de reposição.

    Considera:
    - estoque atual;
    - estoque mínimo;
    - vendas recentes;
    - dias de cobertura;
    - compras pendentes;
    - entregas atrasadas;
    - necessidade líquida de nova compra;
    - fornecedores históricos.

    A ferramenta não cria compras e não altera o estoque.
    """

    try:
        dias_analise_resolvido = (
            _converter_inteiro_positivo(
                dias_analise,
                "dias_analise",
            )
        )

        dias_cobertura_resolvido = (
            _converter_inteiro_positivo(
                dias_cobertura_desejada,
                "dias_cobertura_desejada",
            )
        )

        with SessionLocal() as sessao:
            analises_estoque = (
                listar_analises_estoque(
                    sessao=sessao,
                    dias_analise=(
                        dias_analise_resolvido
                    ),
                    dias_cobertura_desejada=(
                        dias_cobertura_resolvido
                    ),
                    apenas_ativos=apenas_ativos,
                    apenas_com_alerta=False,
                )
            )

            ranking: list[dict[str, Any]] = []

            for estoque in analises_estoque:
                produto_id = estoque.get(
                    "produto_id"
                )

                produto_nome = estoque.get(
                    "produto_nome"
                )

                if not isinstance(
                    produto_id,
                    int,
                ):
                    continue

                try:
                    reposicao = (
                        recomendar_fornecedor_produto(
                            sessao=sessao,
                            produto_id=produto_id,
                            quantidade=None,
                            dias_analise=(
                                dias_analise_resolvido
                            ),
                            dias_cobertura_desejada=(
                                dias_cobertura_resolvido
                            ),
                        )
                    )

                except Exception as erro_produto:
                    ranking.append(
                        {
                            "produto_id": produto_id,
                            "produto_nome": produto_nome,
                            "erro_analise_reposicao": (
                                str(erro_produto)
                            ),
                            "ordem_prioridade": 99,
                            "nivel_prioridade": (
                                "analise_incompleta"
                            ),
                            "acao_recomendada": (
                                "revisar_dados_do_produto"
                            ),
                        }
                    )

                    continue

                estoque_atual = reposicao.get(
                    "estoque_atual",
                    estoque.get(
                        "quantidade_atual"
                    ),
                )

                estoque_minimo = estoque.get(
                    "estoque_minimo"
                )

                dias_cobertura = estoque.get(
                    "dias_cobertura_estimados"
                )

                media_vendas_diaria = reposicao.get(
                    "media_vendas_diaria",
                    0,
                )

                unidades_pendentes = reposicao.get(
                    "unidades_pendentes",
                    0,
                )

                compra_adicional_necessaria = (
                    reposicao.get(
                        "compra_adicional_necessaria",
                        False,
                    )
                    is True
                )

                quantidade_a_comprar = reposicao.get(
                    "quantidade_a_comprar_apos_pendencias",
                    0,
                )

                compras_pendentes = list(
                    reposicao.get(
                        "compras_pendentes"
                    )
                    or []
                )

                compras_atrasadas = [
                    compra
                    for compra in compras_pendentes
                    if (
                        isinstance(
                            compra,
                            dict,
                        )
                        and compra.get(
                            "entrega_atrasada"
                        )
                        is True
                    )
                ]

                possui_compra_atrasada = bool(
                    compras_atrasadas
                )

                cobertura_muito_baixa = (
                    isinstance(
                        dias_cobertura,
                        (int, float),
                    )
                    and dias_cobertura <= 14
                )

                sem_estoque = (
                    isinstance(
                        estoque_atual,
                        (int, float),
                    )
                    and estoque_atual <= 0
                )

                abaixo_minimo = (
                    isinstance(
                        estoque_atual,
                        (int, float),
                    )
                    and isinstance(
                        estoque_minimo,
                        (int, float),
                    )
                    and estoque_atual
                    < estoque_minimo
                )

                # A ordem menor representa maior prioridade.
                if (
                    compra_adicional_necessaria
                    and sem_estoque
                ):
                    ordem_prioridade = 1
                    nivel_prioridade = (
                        "critica_nova_compra"
                    )
                    acao_recomendada = (
                        "realizar_nova_compra_imediatamente"
                    )

                elif compra_adicional_necessaria:
                    ordem_prioridade = 2
                    nivel_prioridade = (
                        "alta_nova_compra"
                    )
                    acao_recomendada = (
                        "planejar_nova_compra"
                    )

                elif (
                    possui_compra_atrasada
                    and cobertura_muito_baixa
                ):
                    ordem_prioridade = 3
                    nivel_prioridade = (
                        "alta_cobrar_entrega"
                    )
                    acao_recomendada = (
                        "cobrar_ou_renegociar_entrega_atrasada"
                    )

                elif possui_compra_atrasada:
                    ordem_prioridade = 4
                    nivel_prioridade = (
                        "media_cobrar_entrega"
                    )
                    acao_recomendada = (
                        "confirmar_entrega_pendente"
                    )

                elif cobertura_muito_baixa:
                    ordem_prioridade = 5
                    nivel_prioridade = (
                        "media_cobertura_baixa"
                    )
                    acao_recomendada = (
                        "monitorar_e_planejar_reposicao"
                    )

                elif abaixo_minimo:
                    ordem_prioridade = 6
                    nivel_prioridade = (
                        "atencao_estoque_minimo"
                    )
                    acao_recomendada = (
                        "monitorar_estoque"
                    )

                else:
                    ordem_prioridade = 7
                    nivel_prioridade = "normal"
                    acao_recomendada = (
                        "nenhuma_acao_imediata"
                    )

                melhor_fornecedor = reposicao.get(
                    "melhor_fornecedor"
                )

                ranking.append(
                    {
                        "produto_id": produto_id,
                        "produto_nome": (
                            reposicao.get(
                                "produto_nome"
                            )
                            or produto_nome
                        ),
                        "ordem_prioridade": (
                            ordem_prioridade
                        ),
                        "nivel_prioridade": (
                            nivel_prioridade
                        ),
                        "acao_recomendada": (
                            acao_recomendada
                        ),
                        "estoque_atual": estoque_atual,
                        "estoque_minimo": estoque_minimo,
                        "dias_cobertura_estimados": (
                            dias_cobertura
                        ),
                        "media_vendas_diaria": (
                            media_vendas_diaria
                        ),
                        "unidades_pendentes": (
                            unidades_pendentes
                        ),
                        "quantidade_compras_atrasadas": (
                            len(
                                compras_atrasadas
                            )
                        ),
                        "compras_atrasadas": (
                            compras_atrasadas
                        ),
                        "estoque_projetado_com_pendencias": (
                            reposicao.get(
                                "estoque_projetado_com_pendencias"
                            )
                        ),
                        "compra_adicional_necessaria": (
                            compra_adicional_necessaria
                        ),
                        "quantidade_a_comprar": (
                            quantidade_a_comprar
                        ),
                        "melhor_fornecedor": (
                            melhor_fornecedor
                        ),
                        "observacao_preco": (
                            reposicao.get(
                                "observacao_preco"
                            )
                        ),
                    }
                )

            def chave_ordenacao(
                item: dict[str, Any],
            ) -> tuple[Any, ...]:
                cobertura = item.get(
                    "dias_cobertura_estimados"
                )

                if not isinstance(
                    cobertura,
                    (int, float),
                ):
                    cobertura = float("inf")

                vendas = item.get(
                    "media_vendas_diaria"
                )

                if not isinstance(
                    vendas,
                    (int, float),
                ):
                    vendas = 0

                return (
                    item.get(
                        "ordem_prioridade",
                        99,
                    ),
                    cobertura,
                    -vendas,
                    item.get(
                        "produto_nome",
                        "",
                    ),
                )

            ranking.sort(
                key=chave_ordenacao
            )

            produtos_validos = [
                item
                for item in ranking
                if item.get(
                    "ordem_prioridade",
                    99,
                ) < 99
            ]

            produto_prioritario = (
                produtos_validos[0]
                if produtos_validos
                else None
            )

            return {
                "sucesso": True,
                "quantidade_produtos_analisados": (
                    len(
                        analises_estoque
                    )
                ),
                "produto_prioritario": (
                    produto_prioritario
                ),
                "ranking": ranking,
                "criterio_prioridade": [
                    (
                        "1. Ruptura com necessidade líquida "
                        "de nova compra."
                    ),
                    (
                        "2. Necessidade líquida de compra "
                        "após considerar pendências."
                    ),
                    (
                        "3. Cobertura muito baixa com "
                        "entrega atrasada."
                    ),
                    (
                        "4. Compras pendentes atrasadas."
                    ),
                    (
                        "5. Cobertura baixa ou estoque "
                        "abaixo do mínimo."
                    ),
                    (
                        "6. Menor cobertura e maior "
                        "velocidade de vendas."
                    ),
                ],
                "observacao": (
                    "Uma compra atrasada não gera automaticamente "
                    "uma nova compra. A ação pode ser cobrar ou "
                    "renegociar a entrega pendente."
                ),
            }

    except Exception as erro:
        return _resposta_erro(
            erro
        )


@tool
def consultar_alertas_produto(
    produto_id: int,
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: float = 10,
    diferenca_concorrente_alerta_percentual: float = 3,
    incluir_informativos: bool = True,
) -> dict[str, Any]:
    """
    Gera todos os alertas empresariais de um produto.

    Verifica estoque, vendas, margem, compras atrasadas,
    concorrência e disponibilidade de fornecedores.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            alertas = gerar_alertas_produto(
                sessao=sessao,
                produto_id=produto_id,
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

            return {
                "sucesso": True,
                "produto_id": produto_id,
                "quantidade_alertas": len(
                    alertas
                ),
                "resumo": resumo,
                "alertas": alertas,
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_painel_alertas_empresariais(
    dias_analise: int = 30,
    dias_cobertura_desejada: int = 30,
    margem_minima_percentual: float = 10,
    diferenca_concorrente_alerta_percentual: float = 3,
    apenas_ativos: bool = True,
    incluir_informativos: bool = True,
) -> dict[str, Any]:
    """
    Gera um painel consolidado de alertas empresariais.

    Analisa estoque, vendas, margens, compras atrasadas,
    concorrentes e fornecedores de todos os produtos.

    Use esta ferramenta quando o usuário pedir riscos, problemas,
    prioridades, alertas ou uma visão geral da empresa.

    Esta ferramenta é somente leitura.
    """

    try:
        with SessionLocal() as sessao:
            painel = gerar_alertas_empresariais(
                sessao=sessao,
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
                apenas_ativos=apenas_ativos,
                incluir_informativos=(
                    incluir_informativos
                ),
            )

            return {
                "sucesso": True,
                **painel,
            }

    except Exception as erro:
        return _resposta_erro(erro)

FERRAMENTAS_ANALISES = [
    analisar_desconto_produto,
    analisar_descontos_todos_produtos,
    analisar_risco_estoque_produto,
    consultar_alertas_estoque,
    recomendar_fornecedor_para_reposicao,
    analisar_prioridades_reposicao_catalogo,
    consultar_alertas_produto,
    consultar_painel_alertas_empresariais,
]