from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.produto import Produto


def listar_produtos(
    sessao: Session,
    apenas_ativos: bool = True,
) -> list[Produto]:
    """Retorna os produtos cadastrados, ordenados pelo nome."""

    consulta = select(Produto).order_by(Produto.nome)

    if apenas_ativos:
        consulta = consulta.where(Produto.ativo.is_(True))

    return list(sessao.scalars(consulta).all())


def buscar_produto_por_id(
    sessao: Session,
    produto_id: int,
) -> Produto | None:
    """Busca um produto pela chave primária."""

    return sessao.get(Produto, produto_id)


def buscar_produto_por_nome(
    sessao: Session,
    nome: str,
) -> Produto | None:
    """Busca um produto pelo nome completo, ignorando maiúsculas."""

    consulta = select(Produto).where(
        Produto.nome.ilike(nome.strip())
    )

    return sessao.scalar(consulta)


def pesquisar_produtos(
    sessao: Session,
    termo: str,
    apenas_ativos: bool = True,
) -> list[Produto]:
    """
    Pesquisa produtos cujo nome ou marca contenham o termo informado.
    """

    termo_limpo = termo.strip()

    if not termo_limpo:
        return listar_produtos(
            sessao=sessao,
            apenas_ativos=apenas_ativos,
        )

    consulta = (
        select(Produto)
        .where(
            Produto.nome.ilike(f"%{termo_limpo}%")
            | Produto.marca.ilike(f"%{termo_limpo}%")
        )
        .order_by(Produto.nome)
    )

    if apenas_ativos:
        consulta = consulta.where(Produto.ativo.is_(True))

    return list(sessao.scalars(consulta).all())


def cadastrar_produto(
    sessao: Session,
    nome: str,
    marca: str,
    armazenamento_gb: int,
    preco_venda: Decimal,
    descricao: str | None = None,
    categoria: str = "Smartphone",
    ativo: bool = True,
) -> Produto:
    """Cadastra um novo produto no banco."""

    nome_limpo = nome.strip()
    marca_limpa = marca.strip()
    categoria_limpa = categoria.strip()

    if not nome_limpo:
        raise ValueError("O nome do produto não pode estar vazio.")

    if not marca_limpa:
        raise ValueError("A marca do produto não pode estar vazia.")

    if armazenamento_gb <= 0:
        raise ValueError(
            "O armazenamento deve ser maior que zero."
        )

    if preco_venda <= 0:
        raise ValueError(
            "O preço de venda deve ser maior que zero."
        )

    produto_existente = buscar_produto_por_nome(
        sessao=sessao,
        nome=nome_limpo,
    )

    if produto_existente is not None:
        raise ValueError(
            f"Já existe um produto chamado '{nome_limpo}'."
        )

    produto = Produto(
        nome=nome_limpo,
        categoria=categoria_limpa,
        marca=marca_limpa,
        armazenamento_gb=armazenamento_gb,
        descricao=descricao.strip() if descricao else None,
        preco_venda=preco_venda,
        ativo=ativo,
    )

    sessao.add(produto)
    sessao.flush()
    sessao.refresh(produto)

    return produto


def atualizar_produto(
    sessao: Session,
    produto_id: int,
    **dados: Any,
) -> Produto:
    """Atualiza os campos permitidos de um produto."""

    produto = buscar_produto_por_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    campos_permitidos = {
        "nome",
        "categoria",
        "marca",
        "armazenamento_gb",
        "descricao",
        "preco_venda",
        "ativo",
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
                "O nome do produto não pode estar vazio."
            )

        produto_com_mesmo_nome = buscar_produto_por_nome(
            sessao=sessao,
            nome=novo_nome,
        )

        if (
            produto_com_mesmo_nome is not None
            and produto_com_mesmo_nome.id != produto.id
        ):
            raise ValueError(
                f"Já existe um produto chamado '{novo_nome}'."
            )

        dados["nome"] = novo_nome

    if "marca" in dados:
        nova_marca = str(dados["marca"]).strip()

        if not nova_marca:
            raise ValueError(
                "A marca do produto não pode estar vazia."
            )

        dados["marca"] = nova_marca

    if "categoria" in dados:
        nova_categoria = str(dados["categoria"]).strip()

        if not nova_categoria:
            raise ValueError(
                "A categoria não pode estar vazia."
            )

        dados["categoria"] = nova_categoria

    if (
        "armazenamento_gb" in dados
        and int(dados["armazenamento_gb"]) <= 0
    ):
        raise ValueError(
            "O armazenamento deve ser maior que zero."
        )

    if (
        "preco_venda" in dados
        and Decimal(str(dados["preco_venda"])) <= 0
    ):
        raise ValueError(
            "O preço de venda deve ser maior que zero."
        )

    if "descricao" in dados and dados["descricao"] is not None:
        dados["descricao"] = str(dados["descricao"]).strip() or None

    for campo, valor in dados.items():
        setattr(produto, campo, valor)

    sessao.flush()
    sessao.refresh(produto)

    return produto


def desativar_produto(
    sessao: Session,
    produto_id: int,
) -> Produto:
    """
    Desativa um produto sem apagar seu histórico de compras e vendas.
    """

    produto = buscar_produto_por_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    produto.ativo = False
    sessao.flush()
    sessao.refresh(produto)

    return produto


def reativar_produto(
    sessao: Session,
    produto_id: int,
) -> Produto:
    """Reativa um produto anteriormente desativado."""

    produto = buscar_produto_por_id(
        sessao=sessao,
        produto_id=produto_id,
    )

    if produto is None:
        raise ValueError(
            f"Produto com ID {produto_id} não encontrado."
        )

    produto.ativo = True
    sessao.flush()
    sessao.refresh(produto)

    return produto