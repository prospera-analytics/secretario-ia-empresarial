from decimal import Decimal

from database.conexao import SessionLocal
from database.crud.concorrente import (
    atualizar_concorrente,
    buscar_concorrente_por_dominio,
    buscar_menor_preco_concorrente,
    buscar_preco_concorrente_por_id,
    cadastrar_concorrente,
    desativar_concorrente,
    listar_concorrentes,
    listar_precos_concorrentes,
    listar_precos_por_produto,
    marcar_preco_disponivel,
    marcar_preco_indisponivel,
    obter_ou_cadastrar_concorrente,
    reativar_concorrente,
    registrar_preco_concorrente,
)
from database.crud.produto import listar_produtos


def testar_crud_concorrente() -> None:
    with SessionLocal() as sessao:
        try:
            concorrentes = listar_concorrentes(
                sessao=sessao,
                apenas_ativos=False,
            )

            print("\nConcorrentes cadastrados:")

            if not concorrentes:
                print("Nenhum concorrente cadastrado.")

            for concorrente in concorrentes:
                print(
                    concorrente.id,
                    concorrente.nome,
                    concorrente.dominio,
                    concorrente.ativo,
                )

            produtos = listar_produtos(sessao)

            if not produtos:
                raise RuntimeError(
                    "Nenhum produto encontrado para o teste."
                )

            produto = produtos[0]

            concorrente_teste = cadastrar_concorrente(
                sessao=sessao,
                nome="Loja Temporária de Teste",
                dominio=(
                    "https://www.loja-temporaria-teste.com.br"
                    "/smartphones"
                ),
            )

            print("\nConcorrente criado:")
            print(concorrente_teste)

            assert (
                concorrente_teste.dominio
                == "loja-temporaria-teste.com.br"
            )

            concorrente_buscado = (
                buscar_concorrente_por_dominio(
                    sessao=sessao,
                    dominio="www.loja-temporaria-teste.com.br",
                )
            )

            assert concorrente_buscado is not None
            assert concorrente_buscado.id == concorrente_teste.id

            concorrente_existente = (
                obter_ou_cadastrar_concorrente(
                    sessao=sessao,
                    nome="Outro nome ignorado",
                    dominio=(
                        "https://loja-temporaria-teste.com.br"
                        "/produto"
                    ),
                )
            )

            assert (
                concorrente_existente.id
                == concorrente_teste.id
            )

            concorrente_atualizado = atualizar_concorrente(
                sessao=sessao,
                concorrente_id=concorrente_teste.id,
                nome="Loja Temporária Atualizada",
            )

            print("\nConcorrente atualizado:")
            print(concorrente_atualizado)

            preco_teste = registrar_preco_concorrente(
                sessao=sessao,
                produto_id=produto.id,
                concorrente_id=concorrente_teste.id,
                nome_produto_encontrado=produto.nome,
                preco=Decimal("1999.90"),
                moeda="BRL",
                url=(
                    "https://loja-temporaria-teste.com.br"
                    "/smartphone-teste"
                ),
                similaridade=Decimal("0.980"),
                tipo_correspondencia="exato",
                disponivel=True,
            )

            print("\nPreço concorrente registrado:")
            print(preco_teste)

            preco_buscado = buscar_preco_concorrente_por_id(
                sessao=sessao,
                preco_concorrente_id=preco_teste.id,
            )

            assert preco_buscado is not None
            assert preco_buscado.produto.id == produto.id
            assert (
                preco_buscado.concorrente.id
                == concorrente_teste.id
            )
            assert preco_buscado.preco == Decimal("1999.90")

            precos_produto = listar_precos_por_produto(
                sessao=sessao,
                produto_id=produto.id,
            )

            print("\nPreços disponíveis para o produto:")

            for item in precos_produto:
                print(
                    item.concorrente.nome,
                    item.nome_produto_encontrado,
                    f"R$ {item.preco:,.2f}",
                    item.tipo_correspondencia,
                    item.similaridade,
                )

            todos_precos_teste = listar_precos_concorrentes(
                sessao=sessao,
                produto_id=produto.id,
                concorrente_id=concorrente_teste.id,
            )

            assert any(
                item.id == preco_teste.id
                for item in todos_precos_teste
            )

            menor_preco = buscar_menor_preco_concorrente(
                sessao=sessao,
                produto_id=produto.id,
                apenas_correspondencia_exata=True,
            )

            assert menor_preco is not None

            print("\nMenor preço encontrado:")
            print(
                menor_preco.concorrente.nome,
                f"R$ {menor_preco.preco:,.2f}",
            )

            preco_indisponivel = marcar_preco_indisponivel(
                sessao=sessao,
                preco_concorrente_id=preco_teste.id,
            )

            assert preco_indisponivel.disponivel is False

            print("\nPreço marcado como indisponível:")
            print(preco_indisponivel.disponivel)

            preco_disponivel = marcar_preco_disponivel(
                sessao=sessao,
                preco_concorrente_id=preco_teste.id,
            )

            assert preco_disponivel.disponivel is True

            concorrente_desativado = desativar_concorrente(
                sessao=sessao,
                concorrente_id=concorrente_teste.id,
            )

            assert concorrente_desativado.ativo is False

            concorrente_reativado = reativar_concorrente(
                sessao=sessao,
                concorrente_id=concorrente_teste.id,
            )

            assert concorrente_reativado.ativo is True

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_concorrente()