from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from database.models.campanha import Campanha
from database.models.campanha_produto import CampanhaProduto
from database.models.produto import Produto
from database.models.venda import Venda


STATUS_VALIDOS = {
    "planejada",
    "ativa",
    "finalizada",
    "cancelada",
}


def listar_campanhas(
    sessao: Session,
    status: str | None = None,
) -> list[Campanha]:
    """Lista as campanhas ordenadas pela data de início."""

    consulta = select(Campanha).order_by(
        Campanha.data_inicio.desc(),
        Campanha.id.desc(),
    )

    if status is not None:
        status_limpo = status.strip().lower()

        if status_limpo not in STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Valores permitidos: "
                + ", ".join(sorted(STATUS_VALIDOS))
            )

        consulta = consulta.where(
            Campanha.status == status_limpo
        )

    return list(sessao.scalars(consulta).all())


def buscar_campanha_por_id(
    sessao: Session,
    campanha_id: int,
) -> Campanha | None:
    """Busca uma campanha pelo ID."""

    return sessao.get(Campanha, campanha_id)


def buscar_campanha_por_nome(
    sessao: Session,
    nome: str,
) -> Campanha | None:
    """Busca uma campanha pelo nome completo."""

    nome_limpo = nome.strip()

    if not nome_limpo:
        return None

    consulta = select(Campanha).where(
        Campanha.nome.ilike(nome_limpo)
    )

    return sessao.scalar(consulta)


def listar_campanhas_ativas(
    sessao: Session,
    data_referencia: date | None = None,
) -> list[Campanha]:
    """Lista campanhas ativas na data informada."""

    data_consulta = data_referencia or date.today()

    consulta = (
        select(Campanha)
        .where(
            Campanha.status == "ativa",
            Campanha.data_inicio <= data_consulta,
            Campanha.data_fim >= data_consulta,
        )
        .order_by(Campanha.data_fim.asc())
    )

    return list(sessao.scalars(consulta).all())


def cadastrar_campanha(
    sessao: Session,
    nome: str,
    canal: str,
    data_inicio: date,
    data_fim: date,
    investimento: Decimal,
    descricao: str | None = None,
    status: str = "planejada",
) -> Campanha:
    """Cadastra uma nova campanha."""

    nome_limpo = nome.strip()
    canal_limpo = canal.strip()
    status_limpo = status.strip().lower()
    valor_investimento = Decimal(str(investimento))

    if not nome_limpo:
        raise ValueError(
            "O nome da campanha não pode estar vazio."
        )

    if not canal_limpo:
        raise ValueError(
            "O canal da campanha não pode estar vazio."
        )

    if data_fim < data_inicio:
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    if valor_investimento < 0:
        raise ValueError(
            "O investimento não pode ser negativo."
        )

    if status_limpo not in STATUS_VALIDOS:
        raise ValueError(
            "Status inválido. Valores permitidos: "
            + ", ".join(sorted(STATUS_VALIDOS))
        )

    campanha_existente = buscar_campanha_por_nome(
        sessao=sessao,
        nome=nome_limpo,
    )

    if campanha_existente is not None:
        raise ValueError(
            f"Já existe uma campanha chamada '{nome_limpo}'."
        )

    campanha = Campanha(
        nome=nome_limpo,
        descricao=descricao.strip() if descricao else None,
        canal=canal_limpo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        investimento=valor_investimento,
        status=status_limpo,
    )

    sessao.add(campanha)
    sessao.flush()
    sessao.refresh(campanha)

    return campanha


def atualizar_campanha(
    sessao: Session,
    campanha_id: int,
    **dados: Any,
) -> Campanha:
    """Atualiza os campos permitidos de uma campanha."""

    campanha = buscar_campanha_por_id(
        sessao=sessao,
        campanha_id=campanha_id,
    )

    if campanha is None:
        raise ValueError(
            f"Campanha com ID {campanha_id} não encontrada."
        )

    campos_permitidos = {
        "nome",
        "descricao",
        "canal",
        "data_inicio",
        "data_fim",
        "investimento",
        "status",
    }

    campos_invalidos = set(dados) - campos_permitidos

    if campos_invalidos:
        raise ValueError(
            "Campos inválidos para atualização: "
            + ", ".join(sorted(campos_invalidos))
        )

    if "nome" in dados:
        novo_nome = str(dados["nome"]).strip()

        if not novo_nome:
            raise ValueError(
                "O nome da campanha não pode estar vazio."
            )

        campanha_mesmo_nome = buscar_campanha_por_nome(
            sessao=sessao,
            nome=novo_nome,
        )

        if (
            campanha_mesmo_nome is not None
            and campanha_mesmo_nome.id != campanha.id
        ):
            raise ValueError(
                f"Já existe uma campanha chamada '{novo_nome}'."
            )

        dados["nome"] = novo_nome

    if "canal" in dados:
        novo_canal = str(dados["canal"]).strip()

        if not novo_canal:
            raise ValueError(
                "O canal da campanha não pode estar vazio."
            )

        dados["canal"] = novo_canal

    if "descricao" in dados and dados["descricao"] is not None:
        dados["descricao"] = (
            str(dados["descricao"]).strip() or None
        )

    if "status" in dados:
        novo_status = str(dados["status"]).strip().lower()

        if novo_status not in STATUS_VALIDOS:
            raise ValueError(
                "Status inválido. Valores permitidos: "
                + ", ".join(sorted(STATUS_VALIDOS))
            )

        dados["status"] = novo_status

    if "investimento" in dados:
        novo_investimento = Decimal(
            str(dados["investimento"])
        )

        if novo_investimento < 0:
            raise ValueError(
                "O investimento não pode ser negativo."
            )

        dados["investimento"] = novo_investimento

    nova_data_inicio = dados.get(
        "data_inicio",
        campanha.data_inicio,
    )

    nova_data_fim = dados.get(
        "data_fim",
        campanha.data_fim,
    )

    if nova_data_fim < nova_data_inicio:
        raise ValueError(
            "A data final não pode ser anterior à data inicial."
        )

    for campo, valor in dados.items():
        setattr(campanha, campo, valor)

    sessao.flush()
    sessao.refresh(campanha)

    return campanha


def adicionar_produto_campanha(
    sessao: Session,
    campanha_id: int,
    produto_id: int,
    desconto_percentual: Decimal,
) -> CampanhaProduto:
    """Relaciona um produto a uma campanha."""

    campanha = sessao.get(Campanha, campanha_id)

    if campanha is None:
        raise ValueError(
            f"Campanha com ID {campanha_id} não encontrada."
        )

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    if not produto.ativo:
        raise ValueError(
            f"O produto '{produto.nome}' está desativado."
        )

    desconto = Decimal(str(desconto_percentual))

    if desconto < 0 or desconto > 100:
        raise ValueError(
            "O desconto deve estar entre 0 e 100."
        )

    consulta = select(CampanhaProduto).where(
        CampanhaProduto.campanha_id == campanha_id,
        CampanhaProduto.produto_id == produto_id,
    )

    relacionamento_existente = sessao.scalar(consulta)

    if relacionamento_existente is not None:
        raise ValueError(
            "Este produto já está associado à campanha."
        )

    campanha_produto = CampanhaProduto(
        campanha_id=campanha_id,
        produto_id=produto_id,
        desconto_percentual=desconto,
    )

    sessao.add(campanha_produto)
    sessao.flush()
    sessao.refresh(campanha_produto)

    return campanha_produto


def listar_produtos_da_campanha(
    sessao: Session,
    campanha_id: int,
) -> list[CampanhaProduto]:
    """Lista os produtos associados a uma campanha."""

    campanha = buscar_campanha_por_id(
        sessao=sessao,
        campanha_id=campanha_id,
    )

    if campanha is None:
        raise ValueError(
            f"Campanha com ID {campanha_id} não encontrada."
        )

    consulta = (
        select(CampanhaProduto)
        .join(
            Produto,
            Produto.id == CampanhaProduto.produto_id,
        )
        .options(
            joinedload(CampanhaProduto.produto)
        )
        .where(
            CampanhaProduto.campanha_id == campanha_id
        )
        .order_by(
            Produto.nome.asc(),
            CampanhaProduto.id.asc(),
        )
    )

    return list(
        sessao.scalars(consulta).all()
    )


def calcular_faturamento_campanha(
    sessao: Session,
    campanha_id: int,
) -> Decimal:
    """Calcula o faturamento das vendas vinculadas à campanha."""

    campanha = buscar_campanha_por_id(
        sessao=sessao,
        campanha_id=campanha_id,
    )

    if campanha is None:
        raise ValueError(
            f"Campanha com ID {campanha_id} não encontrada."
        )

    consulta = select(
        func.coalesce(
            func.sum(
                Venda.quantidade * Venda.preco_unitario
            ),
            0,
        )
    ).where(
        Venda.campanha_id == campanha_id
    )

    resultado = sessao.scalar(consulta)

    return Decimal(str(resultado))


def calcular_retorno_sobre_investimento(
    sessao: Session,
    campanha_id: int,
) -> Decimal | None:
    """
    Calcula o ROI simplificado da campanha.

    Fórmula:
    ((faturamento - investimento) / investimento) * 100
    """

    campanha = buscar_campanha_por_id(
        sessao=sessao,
        campanha_id=campanha_id,
    )

    if campanha is None:
        raise ValueError(
            f"Campanha com ID {campanha_id} não encontrada."
        )

    investimento = Decimal(campanha.investimento)

    if investimento == 0:
        return None

    faturamento = calcular_faturamento_campanha(
        sessao=sessao,
        campanha_id=campanha_id,
    )

    return (
        (faturamento - investimento)
        / investimento
        * Decimal("100")
    )