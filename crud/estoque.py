from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.models.estoque import Estoque
from database.models.produto import Produto


def listar_estoques(
    sessao: Session,
    apenas_produtos_ativos: bool = True,
) -> list[Estoque]:
    """Lista os registros de estoque com os respectivos produtos."""

    consulta = (
        select(Estoque)
        .options(joinedload(Estoque.produto))
        .join(Estoque.produto)
        .order_by(Produto.nome)
    )

    if apenas_produtos_ativos:
        consulta = consulta.where(Produto.ativo.is_(True))

    return list(sessao.scalars(consulta).all())


def buscar_estoque_por_produto_id(
    sessao: Session,
    produto_id: int,
) -> Estoque | None:
    """Busca o estoque de um produto pelo ID."""

    consulta = (
        select(Estoque)
        .options(joinedload(Estoque.produto))
        .where(Estoque.produto_id == produto_id)
    )

    return sessao.scalar(consulta)


def listar_produtos_abaixo_do_minimo(
    sessao: Session,
) -> list[Estoque]:
    """Retorna produtos cujo estoque está abaixo do mínimo definido."""

    consulta = (
        select(Estoque)
        .options(joinedload(Estoque.produto))
        .join(Estoque.produto)
        .where(
            Estoque.quantidade_atual < Estoque.estoque_minimo,
            Produto.ativo.is_(True),
        )
        .order_by(
            Estoque.quantidade_atual.asc(),
            Produto.nome.asc(),
        )
    )

    return list(sessao.scalars(consulta).all())


def listar_produtos_no_limite(
    sessao: Session,
) -> list[Estoque]:
    """Retorna produtos exatamente no estoque mínimo."""

    consulta = (
        select(Estoque)
        .options(joinedload(Estoque.produto))
        .join(Estoque.produto)
        .where(
            Estoque.quantidade_atual == Estoque.estoque_minimo,
            Produto.ativo.is_(True),
        )
        .order_by(Produto.nome)
    )

    return list(sessao.scalars(consulta).all())


def cadastrar_estoque(
    sessao: Session,
    produto_id: int,
    quantidade_atual: int = 0,
    estoque_minimo: int = 0,
) -> Estoque:
    """Cria o registro de estoque de um produto."""

    produto = sessao.get(Produto, produto_id)

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    estoque_existente = buscar_estoque_por_produto_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if estoque_existente is not None:
        raise ValueError(
            f"O produto '{produto.nome}' já possui estoque cadastrado."
        )

    if quantidade_atual < 0:
        raise ValueError(
            "A quantidade atual não pode ser negativa."
        )

    if estoque_minimo < 0:
        raise ValueError(
            "O estoque mínimo não pode ser negativo."
        )

    estoque = Estoque(
        produto_id=produto_id,
        quantidade_atual=quantidade_atual,
        estoque_minimo=estoque_minimo,
    )

    sessao.add(estoque)
    sessao.flush()
    sessao.refresh(estoque)

    return estoque


def definir_quantidade_estoque(
    sessao: Session,
    produto_id: int,
    nova_quantidade: int,
) -> Estoque:
    """Define diretamente a quantidade atual de um produto."""

    if nova_quantidade < 0:
        raise ValueError(
            "A quantidade do estoque não pode ser negativa."
        )

    estoque = buscar_estoque_por_produto_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if estoque is None:
        raise ValueError(
            f"Estoque do produto com ID {produto_id} não encontrado."
        )

    estoque.quantidade_atual = nova_quantidade

    sessao.flush()
    sessao.refresh(estoque)

    return estoque


def adicionar_ao_estoque(
    sessao: Session,
    produto_id: int,
    quantidade: int,
) -> Estoque:
    """Adiciona unidades ao estoque atual."""

    if quantidade <= 0:
        raise ValueError(
            "A quantidade adicionada deve ser maior que zero."
        )

    estoque = buscar_estoque_por_produto_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if estoque is None:
        raise ValueError(
            f"Estoque do produto com ID {produto_id} não encontrado."
        )

    estoque.quantidade_atual += quantidade

    sessao.flush()
    sessao.refresh(estoque)

    return estoque


def remover_do_estoque(
    sessao: Session,
    produto_id: int,
    quantidade: int,
) -> Estoque:
    """Remove unidades do estoque sem permitir saldo negativo."""

    if quantidade <= 0:
        raise ValueError(
            "A quantidade removida deve ser maior que zero."
        )

    estoque = buscar_estoque_por_produto_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if estoque is None:
        raise ValueError(
            f"Estoque do produto com ID {produto_id} não encontrado."
        )

    if quantidade > estoque.quantidade_atual:
        raise ValueError(
            f"Estoque insuficiente. Quantidade disponível: "
            f"{estoque.quantidade_atual}."
        )

    estoque.quantidade_atual -= quantidade

    sessao.flush()
    sessao.refresh(estoque)

    return estoque


def atualizar_estoque_minimo(
    sessao: Session,
    produto_id: int,
    novo_estoque_minimo: int,
) -> Estoque:
    """Atualiza o limite mínimo de estoque de um produto."""

    if novo_estoque_minimo < 0:
        raise ValueError(
            "O estoque mínimo não pode ser negativo."
        )

    estoque = buscar_estoque_por_produto_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if estoque is None:
        raise ValueError(
            f"Estoque do produto com ID {produto_id} não encontrado."
        )

    estoque.estoque_minimo = novo_estoque_minimo

    sessao.flush()
    sessao.refresh(estoque)

    return estoque