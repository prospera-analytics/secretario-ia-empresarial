from uuid import uuid4

from database.conexao import SessionLocal
from database.models.concorrente import Concorrente

from agente.ferramentas.concorrente import (
    consultar_concorrente_por_dominio,
    consultar_concorrente_por_id,
    consultar_concorrentes,
    criar_concorrente,
    desativar_cadastro_concorrente,
    modificar_concorrente,
    obter_ou_criar_concorrente,
    reativar_cadastro_concorrente,
)


def excluir_concorrente_teste(
    concorrente_id: int,
) -> None:
    """Remove o concorrente temporário criado pelo teste."""

    with SessionLocal() as sessao:
        try:
            concorrente = sessao.get(
                Concorrente,
                concorrente_id,
            )

            if concorrente is not None:
                sessao.delete(concorrente)
                sessao.commit()

        except Exception:
            sessao.rollback()
            raise


def testar_ferramentas_concorrente() -> None:
    """Testa as ferramentas de cadastro de concorrentes."""

    identificador = uuid4().hex[:8]

    nome_inicial = (
        f"Concorrente Teste {identificador}"
    )

    nome_atualizado = (
        f"Concorrente Atualizado {identificador}"
    )

    dominio_inicial = (
        f"www.concorrente-{identificador}.com.br"
    )

    dominio_normalizado = (
        f"concorrente-{identificador}.com.br"
    )

    novo_dominio = (
        f"loja-{identificador}.com.br"
    )

    concorrente_id: int | None = None

    try:
        resultado_criacao = criar_concorrente.invoke(
            {
                "nome": nome_inicial,
                "dominio": (
                    f"https://{dominio_inicial}/smartphones"
                ),
                "ativo": True,
            }
        )

        print("\nResultado da criação:")
        print(resultado_criacao)

        assert resultado_criacao["sucesso"] is True

        concorrente = resultado_criacao["concorrente"]
        concorrente_id = concorrente["id"]

        assert concorrente["nome"] == nome_inicial
        assert (
            concorrente["dominio"]
            == dominio_normalizado
        )
        assert concorrente["ativo"] is True

        resultado_por_id = (
            consultar_concorrente_por_id.invoke(
                {
                    "concorrente_id": concorrente_id,
                }
            )
        )

        print("\nConsulta por ID:")
        print(resultado_por_id)

        assert resultado_por_id["sucesso"] is True
        assert (
            resultado_por_id["concorrente"]["id"]
            == concorrente_id
        )

        resultado_por_dominio = (
            consultar_concorrente_por_dominio.invoke(
                {
                    "dominio": (
                        f"https://www."
                        f"{dominio_normalizado}/produto"
                    ),
                }
            )
        )

        print("\nConsulta por domínio:")
        print(resultado_por_dominio)

        assert resultado_por_dominio["sucesso"] is True
        assert (
            resultado_por_dominio["concorrente"]["id"]
            == concorrente_id
        )

        resultado_obter = (
            obter_ou_criar_concorrente.invoke(
                {
                    "nome": "Nome que não deve substituir",
                    "dominio": dominio_normalizado,
                }
            )
        )

        print("\nObter concorrente existente:")
        print(resultado_obter)

        assert resultado_obter["sucesso"] is True
        assert resultado_obter["criado"] is False
        assert (
            resultado_obter["concorrente"]["id"]
            == concorrente_id
        )
        assert (
            resultado_obter["concorrente"]["nome"]
            == nome_inicial
        )

        resultado_lista = consultar_concorrentes.invoke(
            {
                "apenas_ativos": True,
            }
        )

        print("\nLista de concorrentes ativos:")
        print(resultado_lista)

        assert resultado_lista["sucesso"] is True

        ids_ativos = {
            item["id"]
            for item in resultado_lista["concorrentes"]
        }

        assert concorrente_id in ids_ativos

        resultado_atualizacao = (
            modificar_concorrente.invoke(
                {
                    "concorrente_id": concorrente_id,
                    "nome": nome_atualizado,
                    "dominio": (
                        f"https://www.{novo_dominio}/ofertas"
                    ),
                }
            )
        )

        print("\nResultado da atualização:")
        print(resultado_atualizacao)

        assert resultado_atualizacao["sucesso"] is True

        concorrente_atualizado = (
            resultado_atualizacao["concorrente"]
        )

        assert (
            concorrente_atualizado["nome"]
            == nome_atualizado
        )
        assert (
            concorrente_atualizado["dominio"]
            == novo_dominio
        )

        resultado_desativacao = (
            desativar_cadastro_concorrente.invoke(
                {
                    "concorrente_id": concorrente_id,
                }
            )
        )

        print("\nResultado da desativação:")
        print(resultado_desativacao)

        assert resultado_desativacao["sucesso"] is True
        assert (
            resultado_desativacao["concorrente"]["ativo"]
            is False
        )

        lista_ativos = consultar_concorrentes.invoke(
            {
                "apenas_ativos": True,
            }
        )

        ids_ativos = {
            item["id"]
            for item in lista_ativos["concorrentes"]
        }

        assert concorrente_id not in ids_ativos

        lista_com_inativos = (
            consultar_concorrentes.invoke(
                {
                    "apenas_ativos": False,
                }
            )
        )

        ids_todos = {
            item["id"]
            for item in lista_com_inativos["concorrentes"]
        }

        assert concorrente_id in ids_todos

        resultado_reativacao = (
            reativar_cadastro_concorrente.invoke(
                {
                    "concorrente_id": concorrente_id,
                }
            )
        )

        print("\nResultado da reativação:")
        print(resultado_reativacao)

        assert resultado_reativacao["sucesso"] is True
        assert (
            resultado_reativacao["concorrente"]["ativo"]
            is True
        )

        print(
            "\nTodos os testes das ferramentas "
            "de concorrente passaram."
        )

    finally:
        if concorrente_id is not None:
            excluir_concorrente_teste(
                concorrente_id=concorrente_id,
            )

            print(
                "\nO concorrente criado pelo teste "
                "foi removido."
            )


if __name__ == "__main__":
    testar_ferramentas_concorrente()