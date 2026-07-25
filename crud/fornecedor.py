from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.fornecedor import Fornecedor


def listar_fornecedores(
    sessao: Session,
    apenas_ativos: bool = True,
) -> list[Fornecedor]:
    """Lista os fornecedores ordenados pelo nome."""

    consulta = select(Fornecedor).order_by(Fornecedor.nome)

    if apenas_ativos:
        consulta = consulta.where(Fornecedor.ativo.is_(True))

    return list(sessao.scalars(consulta).all())


def buscar_fornecedor_por_id(
    sessao: Session,
    fornecedor_id: int,
) -> Fornecedor | None:
    """Busca um fornecedor pela chave primária."""

    return sessao.get(Fornecedor, fornecedor_id)


def buscar_fornecedor_por_nome(
    sessao: Session,
    nome: str,
) -> Fornecedor | None:
    """Busca um fornecedor pelo nome completo."""

    nome_limpo = nome.strip()

    if not nome_limpo:
        return None

    consulta = select(Fornecedor).where(
        Fornecedor.nome.ilike(nome_limpo)
    )

    return sessao.scalar(consulta)


def pesquisar_fornecedores(
    sessao: Session,
    termo: str,
    apenas_ativos: bool = True,
) -> list[Fornecedor]:
    """
    Pesquisa fornecedores por nome, cidade ou estado.
    """

    termo_limpo = termo.strip()

    if not termo_limpo:
        return listar_fornecedores(
            sessao=sessao,
            apenas_ativos=apenas_ativos,
        )

    consulta = (
        select(Fornecedor)
        .where(
            Fornecedor.nome.ilike(f"%{termo_limpo}%")
            | Fornecedor.cidade.ilike(f"%{termo_limpo}%")
            | Fornecedor.estado.ilike(f"%{termo_limpo}%")
        )
        .order_by(Fornecedor.nome)
    )

    if apenas_ativos:
        consulta = consulta.where(Fornecedor.ativo.is_(True))

    return list(sessao.scalars(consulta).all())


def cadastrar_fornecedor(
    sessao: Session,
    nome: str,
    cidade: str,
    estado: str,
    prazo_entrega_dias: int,
    ativo: bool = True,
) -> Fornecedor:
    """Cadastra um novo fornecedor."""

    nome_limpo = nome.strip()
    cidade_limpa = cidade.strip()
    estado_limpo = estado.strip().upper()

    if not nome_limpo:
        raise ValueError(
            "O nome do fornecedor não pode estar vazio."
        )

    if not cidade_limpa:
        raise ValueError(
            "A cidade do fornecedor não pode estar vazia."
        )

    if len(estado_limpo) != 2:
        raise ValueError(
            "O estado deve ser informado pela sigla com 2 letras."
        )

    if prazo_entrega_dias < 0:
        raise ValueError(
            "O prazo de entrega não pode ser negativo."
        )

    fornecedor_existente = buscar_fornecedor_por_nome(
        sessao=sessao,
        nome=nome_limpo,
    )

    if fornecedor_existente is not None:
        raise ValueError(
            f"Já existe um fornecedor chamado '{nome_limpo}'."
        )

    fornecedor = Fornecedor(
        nome=nome_limpo,
        cidade=cidade_limpa,
        estado=estado_limpo,
        prazo_entrega_dias=prazo_entrega_dias,
        ativo=ativo,
    )

    sessao.add(fornecedor)
    sessao.flush()
    sessao.refresh(fornecedor)

    return fornecedor


def atualizar_fornecedor(
    sessao: Session,
    fornecedor_id: int,
    **dados: Any,
) -> Fornecedor:
    """Atualiza os campos permitidos de um fornecedor."""

    fornecedor = buscar_fornecedor_por_id(
        sessao=sessao,
        fornecedor_id=fornecedor_id,
    )

    if fornecedor is None:
        raise ValueError(
            f"Fornecedor com ID {fornecedor_id} não encontrado."
        )

    campos_permitidos = {
        "nome",
        "cidade",
        "estado",
        "prazo_entrega_dias",
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
                "O nome do fornecedor não pode estar vazio."
            )

        fornecedor_mesmo_nome = buscar_fornecedor_por_nome(
            sessao=sessao,
            nome=novo_nome,
        )

        if (
            fornecedor_mesmo_nome is not None
            and fornecedor_mesmo_nome.id != fornecedor.id
        ):
            raise ValueError(
                f"Já existe um fornecedor chamado '{novo_nome}'."
            )

        dados["nome"] = novo_nome

    if "cidade" in dados:
        nova_cidade = str(dados["cidade"]).strip()

        if not nova_cidade:
            raise ValueError(
                "A cidade do fornecedor não pode estar vazia."
            )

        dados["cidade"] = nova_cidade

    if "estado" in dados:
        novo_estado = str(dados["estado"]).strip().upper()

        if len(novo_estado) != 2:
            raise ValueError(
                "O estado deve ser informado pela sigla com 2 letras."
            )

        dados["estado"] = novo_estado

    if (
        "prazo_entrega_dias" in dados
        and int(dados["prazo_entrega_dias"]) < 0
    ):
        raise ValueError(
            "O prazo de entrega não pode ser negativo."
        )

    for campo, valor in dados.items():
        setattr(fornecedor, campo, valor)

    sessao.flush()
    sessao.refresh(fornecedor)

    return fornecedor


def desativar_fornecedor(
    sessao: Session,
    fornecedor_id: int,
) -> Fornecedor:
    """Desativa um fornecedor sem apagar seu histórico."""

    fornecedor = buscar_fornecedor_por_id(
        sessao=sessao,
        fornecedor_id=fornecedor_id,
    )

    if fornecedor is None:
        raise ValueError(
            f"Fornecedor com ID {fornecedor_id} não encontrado."
        )

    fornecedor.ativo = False

    sessao.flush()
    sessao.refresh(fornecedor)

    return fornecedor


def reativar_fornecedor(
    sessao: Session,
    fornecedor_id: int,
) -> Fornecedor:
    """Reativa um fornecedor desativado."""

    fornecedor = buscar_fornecedor_por_id(
        sessao=sessao,
        fornecedor_id=fornecedor_id,
    )

    if fornecedor is None:
        raise ValueError(
            f"Fornecedor com ID {fornecedor_id} não encontrado."
        )

    fornecedor.ativo = True

    sessao.flush()
    sessao.refresh(fornecedor)

    return fornecedor