from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.tools import tool

from crud.campanha import (
    adicionar_produto_campanha,
    atualizar_campanha,
    buscar_campanha_por_id,
    buscar_campanha_por_nome,
    cadastrar_campanha,
    calcular_faturamento_campanha,
    calcular_retorno_sobre_investimento,
    listar_campanhas,
    listar_campanhas_ativas,
    listar_produtos_da_campanha,
)
from database.conexao import SessionLocal


def _converter_data_iso(
    valor: str | None,
    nome_campo: str,
) -> date | None:
    """Converte uma string AAAA-MM-DD em date."""

    if valor is None:
        return None

    valor_limpo = valor.strip()

    if not valor_limpo:
        return None

    try:
        return date.fromisoformat(valor_limpo)

    except ValueError as erro:
        raise ValueError(
            f"{nome_campo} inválida. "
            "Use o formato AAAA-MM-DD."
        ) from erro


def _converter_decimal(
    valor: float | int | str,
    nome_campo: str,
) -> Decimal:
    """Converte um valor numérico para Decimal."""

    try:
        return Decimal(str(valor))

    except (InvalidOperation, ValueError, TypeError) as erro:
        raise ValueError(
            f"{nome_campo} inválido."
        ) from erro


def _campanha_para_dict(
    campanha: Any,
) -> dict[str, Any]:
    """Converte uma campanha em dicionário serializável."""

    investimento = Decimal(
        str(campanha.investimento)
    )

    return {
        "id": campanha.id,
        "nome": campanha.nome,
        "descricao": campanha.descricao,
        "canal": campanha.canal,
        "data_inicio": campanha.data_inicio.isoformat(),
        "data_fim": campanha.data_fim.isoformat(),
        "investimento": float(investimento),
        "status": campanha.status,
    }


def _campanha_produto_para_dict(
    campanha_produto: Any,
) -> dict[str, Any]:
    """Converte uma associação campanha-produto."""

    produto = getattr(
        campanha_produto,
        "produto",
        None,
    )

    desconto = Decimal(
        str(campanha_produto.desconto_percentual)
    )

    preco_original = None
    preco_com_desconto = None

    if produto is not None:
        preco_original_decimal = Decimal(
            str(produto.preco_venda)
        )

        multiplicador = (
            Decimal("1")
            - desconto / Decimal("100")
        )

        preco_desconto_decimal = (
            preco_original_decimal * multiplicador
        )

        preco_original = float(
            preco_original_decimal
        )

        preco_com_desconto = float(
            preco_desconto_decimal.quantize(
                Decimal("0.01")
            )
        )

    return {
        "id": campanha_produto.id,
        "campanha_id": campanha_produto.campanha_id,
        "produto_id": campanha_produto.produto_id,
        "produto_nome": (
            produto.nome
            if produto is not None
            else None
        ),
        "produto_marca": (
            produto.marca
            if produto is not None
            else None
        ),
        "armazenamento_gb": (
            produto.armazenamento_gb
            if produto is not None
            else None
        ),
        "desconto_percentual": float(desconto),
        "preco_original": preco_original,
        "preco_com_desconto": preco_com_desconto,
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza respostas de erro."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def consultar_campanhas(
    status: str | None = None,
) -> dict[str, Any]:
    """
    Lista campanhas registradas no banco.

    Pode filtrar pelos status: planejada, ativa, finalizada
    ou cancelada. Sem status, retorna todas as campanhas.
    """

    try:
        with SessionLocal() as sessao:
            campanhas = listar_campanhas(
                sessao=sessao,
                status=status,
            )

            return {
                "sucesso": True,
                "filtro_status": status,
                "quantidade": len(campanhas),
                "campanhas": [
                    _campanha_para_dict(campanha)
                    for campanha in campanhas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_campanha_por_id(
    campanha_id: int,
) -> dict[str, Any]:
    """Busca uma campanha pelo ID interno."""

    try:
        with SessionLocal() as sessao:
            campanha = buscar_campanha_por_id(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            if campanha is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Campanha com ID {campanha_id} "
                        "não encontrada."
                    ),
                }

            return {
                "sucesso": True,
                "campanha": _campanha_para_dict(
                    campanha
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_campanha_por_nome(
    nome: str,
) -> dict[str, Any]:
    """Busca uma campanha pelo nome completo."""

    try:
        with SessionLocal() as sessao:
            campanha = buscar_campanha_por_nome(
                sessao=sessao,
                nome=nome,
            )

            if campanha is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Campanha chamada '{nome}' "
                        "não encontrada."
                    ),
                }

            return {
                "sucesso": True,
                "campanha": _campanha_para_dict(
                    campanha
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_campanhas_ativas(
    data_referencia: str | None = None,
) -> dict[str, Any]:
    """
    Lista campanhas ativas em uma determinada data.

    A data deve estar no formato AAAA-MM-DD. Quando não informada,
    utiliza a data atual.
    """

    try:
        data_convertida = _converter_data_iso(
            valor=data_referencia,
            nome_campo="Data de referência",
        )

        with SessionLocal() as sessao:
            campanhas = listar_campanhas_ativas(
                sessao=sessao,
                data_referencia=data_convertida,
            )

            data_consulta = (
                data_convertida or date.today()
            )

            return {
                "sucesso": True,
                "data_referencia": (
                    data_consulta.isoformat()
                ),
                "quantidade": len(campanhas),
                "campanhas": [
                    _campanha_para_dict(campanha)
                    for campanha in campanhas
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def criar_campanha(
    nome: str,
    canal: str,
    data_inicio: str,
    data_fim: str,
    investimento: float,
    descricao: str | None = None,
    status: str = "planejada",
) -> dict[str, Any]:
    """
    Cadastra uma nova campanha promocional.

    As datas devem estar no formato AAAA-MM-DD.

    Os status permitidos são: planejada, ativa, finalizada
    e cancelada.
    """

    try:
        inicio = _converter_data_iso(
            valor=data_inicio,
            nome_campo="Data inicial",
        )

        fim = _converter_data_iso(
            valor=data_fim,
            nome_campo="Data final",
        )

        if inicio is None:
            raise ValueError(
                "A data inicial é obrigatória."
            )

        if fim is None:
            raise ValueError(
                "A data final é obrigatória."
            )

        investimento_decimal = _converter_decimal(
            valor=investimento,
            nome_campo="Investimento",
        )

        with SessionLocal() as sessao:
            try:
                campanha = cadastrar_campanha(
                    sessao=sessao,
                    nome=nome,
                    canal=canal,
                    data_inicio=inicio,
                    data_fim=fim,
                    investimento=investimento_decimal,
                    descricao=descricao,
                    status=status,
                )

                campanha_id = campanha.id

                sessao.commit()

                campanha_salva = buscar_campanha_por_id(
                    sessao=sessao,
                    campanha_id=campanha_id,
                )

                if campanha_salva is None:
                    raise RuntimeError(
                        "A campanha foi criada, mas não pôde "
                        "ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Campanha criada com sucesso."
                    ),
                    "campanha": _campanha_para_dict(
                        campanha_salva
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_campanha(
    campanha_id: int,
    nome: str | None = None,
    descricao: str | None = None,
    canal: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    investimento: float | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """
    Atualiza os dados de uma campanha existente.

    Somente os campos informados serão modificados. As datas devem
    estar no formato AAAA-MM-DD.
    """

    try:
        dados: dict[str, Any] = {}

        if nome is not None:
            dados["nome"] = nome

        if descricao is not None:
            dados["descricao"] = descricao

        if canal is not None:
            dados["canal"] = canal

        if data_inicio is not None:
            inicio = _converter_data_iso(
                valor=data_inicio,
                nome_campo="Data inicial",
            )

            if inicio is None:
                raise ValueError(
                    "A data inicial informada é inválida."
                )

            dados["data_inicio"] = inicio

        if data_fim is not None:
            fim = _converter_data_iso(
                valor=data_fim,
                nome_campo="Data final",
            )

            if fim is None:
                raise ValueError(
                    "A data final informada é inválida."
                )

            dados["data_fim"] = fim

        if investimento is not None:
            dados["investimento"] = _converter_decimal(
                valor=investimento,
                nome_campo="Investimento",
            )

        if status is not None:
            dados["status"] = status

        if not dados:
            raise ValueError(
                "Nenhum campo foi informado para atualização."
            )

        with SessionLocal() as sessao:
            try:
                atualizar_campanha(
                    sessao=sessao,
                    campanha_id=campanha_id,
                    **dados,
                )

                sessao.commit()

                campanha = buscar_campanha_por_id(
                    sessao=sessao,
                    campanha_id=campanha_id,
                )

                if campanha is None:
                    raise RuntimeError(
                        "A campanha foi atualizada, mas não pôde "
                        "ser consultada novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Campanha atualizada com sucesso."
                    ),
                    "campanha": _campanha_para_dict(
                        campanha
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def associar_produto_campanha(
    campanha_id: int,
    produto_id: int,
    desconto_percentual: float,
) -> dict[str, Any]:
    """
    Associa um produto a uma campanha promocional.

    O desconto percentual deve estar entre 0 e 100.
    O produto precisa existir e estar ativo.
    """

    try:
        desconto = _converter_decimal(
            valor=desconto_percentual,
            nome_campo="Desconto percentual",
        )

        with SessionLocal() as sessao:
            try:
                relacionamento = adicionar_produto_campanha(
                    sessao=sessao,
                    campanha_id=campanha_id,
                    produto_id=produto_id,
                    desconto_percentual=desconto,
                )

                relacionamento_id = relacionamento.id

                sessao.commit()

                produtos = listar_produtos_da_campanha(
                    sessao=sessao,
                    campanha_id=campanha_id,
                )

                relacionamento_salvo = next(
                    (
                        item
                        for item in produtos
                        if item.id == relacionamento_id
                    ),
                    None,
                )

                if relacionamento_salvo is None:
                    raise RuntimeError(
                        "O produto foi associado, mas a "
                        "associação não pôde ser consultada."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Produto associado à campanha "
                        "com sucesso."
                    ),
                    "associacao": (
                        _campanha_produto_para_dict(
                            relacionamento_salvo
                        )
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_produtos_campanha(
    campanha_id: int,
) -> dict[str, Any]:
    """Lista os produtos associados a uma campanha."""

    try:
        with SessionLocal() as sessao:
            produtos = listar_produtos_da_campanha(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            return {
                "sucesso": True,
                "campanha_id": campanha_id,
                "quantidade": len(produtos),
                "produtos": [
                    _campanha_produto_para_dict(item)
                    for item in produtos
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_resultado_campanha(
    campanha_id: int,
) -> dict[str, Any]:
    """
    Calcula o faturamento e o ROI simplificado de uma campanha.

    O ROI é calculado por:
    ((faturamento - investimento) / investimento) * 100.

    Quando o investimento é zero, o ROI será nulo.
    """

    try:
        with SessionLocal() as sessao:
            campanha = buscar_campanha_por_id(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            if campanha is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Campanha com ID {campanha_id} "
                        "não encontrada."
                    ),
                }

            faturamento = calcular_faturamento_campanha(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            roi = calcular_retorno_sobre_investimento(
                sessao=sessao,
                campanha_id=campanha_id,
            )

            return {
                "sucesso": True,
                "campanha": _campanha_para_dict(
                    campanha
                ),
                "faturamento": float(faturamento),
                "roi_percentual": (
                    float(roi)
                    if roi is not None
                    else None
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_CAMPANHA = [
    consultar_campanhas,
    consultar_campanha_por_id,
    consultar_campanha_por_nome,
    consultar_campanhas_ativas,
    criar_campanha,
    modificar_campanha,
    associar_produto_campanha,
    consultar_produtos_campanha,
    consultar_resultado_campanha,
]