from typing import Any

from langchain_core.tools import tool

from crud.concorrente import (
    atualizar_concorrente,
    buscar_concorrente_por_dominio,
    buscar_concorrente_por_id,
    cadastrar_concorrente,
    desativar_concorrente,
    listar_concorrentes,
    obter_ou_cadastrar_concorrente,
    reativar_concorrente,
)
from database.conexao import SessionLocal


def _concorrente_para_dict(
    concorrente: Any,
) -> dict[str, Any]:
    """Converte um concorrente em dicionário serializável."""

    return {
        "id": concorrente.id,
        "nome": concorrente.nome,
        "dominio": concorrente.dominio,
        "ativo": concorrente.ativo,
        "criado_em": (
            concorrente.criado_em.isoformat()
            if concorrente.criado_em is not None
            else None
        ),
        "atualizado_em": (
            concorrente.atualizado_em.isoformat()
            if concorrente.atualizado_em is not None
            else None
        ),
    }


def _resposta_erro(
    erro: Exception,
) -> dict[str, Any]:
    """Padroniza as respostas de erro das ferramentas."""

    return {
        "sucesso": False,
        "erro": str(erro),
    }


@tool
def consultar_concorrentes(
    apenas_ativos: bool = True,
) -> dict[str, Any]:
    """
    Lista os concorrentes cadastrados.

    Por padrão, retorna apenas concorrentes ativos.
    Use apenas_ativos=False para incluir concorrentes desativados.
    """

    try:
        with SessionLocal() as sessao:
            concorrentes = listar_concorrentes(
                sessao=sessao,
                apenas_ativos=apenas_ativos,
            )

            return {
                "sucesso": True,
                "apenas_ativos": apenas_ativos,
                "quantidade": len(concorrentes),
                "concorrentes": [
                    _concorrente_para_dict(concorrente)
                    for concorrente in concorrentes
                ],
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_concorrente_por_id(
    concorrente_id: int,
) -> dict[str, Any]:
    """Busca um concorrente pelo ID interno."""

    try:
        with SessionLocal() as sessao:
            concorrente = buscar_concorrente_por_id(
                sessao=sessao,
                concorrente_id=concorrente_id,
            )

            if concorrente is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Concorrente com ID {concorrente_id} "
                        "não encontrado."
                    ),
                }

            return {
                "sucesso": True,
                "concorrente": _concorrente_para_dict(
                    concorrente
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def consultar_concorrente_por_dominio(
    dominio: str,
) -> dict[str, Any]:
    """
    Busca um concorrente pelo domínio.

    O domínio pode ser informado como URL completa, com www,
    ou apenas como domínio.
    """

    try:
        with SessionLocal() as sessao:
            concorrente = buscar_concorrente_por_dominio(
                sessao=sessao,
                dominio=dominio,
            )

            if concorrente is None:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Nenhum concorrente foi encontrado "
                        f"para o domínio '{dominio}'."
                    ),
                }

            return {
                "sucesso": True,
                "concorrente": _concorrente_para_dict(
                    concorrente
                ),
            }

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def criar_concorrente(
    nome: str,
    dominio: str,
    ativo: bool = True,
) -> dict[str, Any]:
    """
    Cadastra um novo concorrente.

    O domínio será normalizado automaticamente. Por exemplo,
    https://www.exemplo.com.br/produto será armazenado como
    exemplo.com.br.
    """

    try:
        with SessionLocal() as sessao:
            try:
                concorrente = cadastrar_concorrente(
                    sessao=sessao,
                    nome=nome,
                    dominio=dominio,
                    ativo=ativo,
                )

                concorrente_id = concorrente.id

                sessao.commit()

                concorrente_salvo = buscar_concorrente_por_id(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                )

                if concorrente_salvo is None:
                    raise RuntimeError(
                        "O concorrente foi criado, mas não pôde "
                        "ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Concorrente criado com sucesso."
                    ),
                    "concorrente": _concorrente_para_dict(
                        concorrente_salvo
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def obter_ou_criar_concorrente(
    nome: str,
    dominio: str,
) -> dict[str, Any]:
    """
    Retorna o concorrente do domínio informado ou cria um novo.

    Esta ferramenta é útil durante coletas automáticas de preços,
    pois evita cadastrar o mesmo domínio mais de uma vez.
    """

    try:
        with SessionLocal() as sessao:
            try:
                concorrente_existente = (
                    buscar_concorrente_por_dominio(
                        sessao=sessao,
                        dominio=dominio,
                    )
                )

                criado = concorrente_existente is None

                concorrente = obter_ou_cadastrar_concorrente(
                    sessao=sessao,
                    nome=nome,
                    dominio=dominio,
                )

                concorrente_id = concorrente.id

                sessao.commit()

                concorrente_salvo = buscar_concorrente_por_id(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                )

                if concorrente_salvo is None:
                    raise RuntimeError(
                        "O concorrente não pôde ser consultado "
                        "após a operação."
                    )

                return {
                    "sucesso": True,
                    "criado": criado,
                    "mensagem": (
                        "Concorrente criado com sucesso."
                        if criado
                        else "Concorrente já estava cadastrado."
                    ),
                    "concorrente": _concorrente_para_dict(
                        concorrente_salvo
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def modificar_concorrente(
    concorrente_id: int,
    nome: str | None = None,
    dominio: str | None = None,
    ativo: bool | None = None,
) -> dict[str, Any]:
    """
    Atualiza os dados de um concorrente.

    Somente os campos informados serão alterados.
    """

    try:
        if (
            nome is None
            and dominio is None
            and ativo is None
        ):
            raise ValueError(
                "Nenhum campo foi informado para atualização."
            )

        with SessionLocal() as sessao:
            try:
                atualizar_concorrente(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                    nome=nome,
                    dominio=dominio,
                    ativo=ativo,
                )

                sessao.commit()

                concorrente = buscar_concorrente_por_id(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                )

                if concorrente is None:
                    raise RuntimeError(
                        "O concorrente foi atualizado, mas não "
                        "pôde ser consultado novamente."
                    )

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Concorrente atualizado com sucesso."
                    ),
                    "concorrente": _concorrente_para_dict(
                        concorrente
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def desativar_cadastro_concorrente(
    concorrente_id: int,
) -> dict[str, Any]:
    """
    Desativa um concorrente sem apagar seu histórico de preços.
    """

    try:
        with SessionLocal() as sessao:
            try:
                concorrente = desativar_concorrente(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                )

                sessao.commit()

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Concorrente desativado com sucesso."
                    ),
                    "concorrente": _concorrente_para_dict(
                        concorrente
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


@tool
def reativar_cadastro_concorrente(
    concorrente_id: int,
) -> dict[str, Any]:
    """Reativa um concorrente anteriormente desativado."""

    try:
        with SessionLocal() as sessao:
            try:
                concorrente = reativar_concorrente(
                    sessao=sessao,
                    concorrente_id=concorrente_id,
                )

                sessao.commit()

                return {
                    "sucesso": True,
                    "mensagem": (
                        "Concorrente reativado com sucesso."
                    ),
                    "concorrente": _concorrente_para_dict(
                        concorrente
                    ),
                }

            except Exception:
                sessao.rollback()
                raise

    except Exception as erro:
        return _resposta_erro(erro)


FERRAMENTAS_CONCORRENTE = [
    consultar_concorrentes,
    consultar_concorrente_por_id,
    consultar_concorrente_por_dominio,
    criar_concorrente,
    obter_ou_criar_concorrente,
    modificar_concorrente,
    desativar_cadastro_concorrente,
    reativar_cadastro_concorrente,
]