from database.conexao import SessionLocal
from database.crud.fornecedor import (
    atualizar_fornecedor,
    buscar_fornecedor_por_id,
    cadastrar_fornecedor,
    desativar_fornecedor,
    listar_fornecedores,
    pesquisar_fornecedores,
    reativar_fornecedor,
)


def testar_crud_fornecedor() -> None:
    with SessionLocal() as sessao:
        try:
            fornecedores = listar_fornecedores(sessao)

            print("\nFornecedores cadastrados:")

            for fornecedor in fornecedores:
                print(
                    fornecedor.id,
                    fornecedor.nome,
                    fornecedor.cidade,
                    fornecedor.estado,
                    f"{fornecedor.prazo_entrega_dias} dias",
                )

            fornecedores_sp = pesquisar_fornecedores(
                sessao=sessao,
                termo="SP",
            )

            print("\nFornecedores encontrados em SP:")

            for fornecedor in fornecedores_sp:
                print(
                    fornecedor.nome,
                    fornecedor.cidade,
                )

            fornecedor_teste = cadastrar_fornecedor(
                sessao=sessao,
                nome="Fornecedor de Teste",
                cidade="São José dos Campos",
                estado="sp",
                prazo_entrega_dias=4,
            )

            print("\nFornecedor criado:")
            print(fornecedor_teste)

            fornecedor_atualizado = atualizar_fornecedor(
                sessao=sessao,
                fornecedor_id=fornecedor_teste.id,
                prazo_entrega_dias=3,
                cidade="Taubaté",
            )

            print("\nFornecedor atualizado:")
            print(fornecedor_atualizado)

            fornecedor_buscado = buscar_fornecedor_por_id(
                sessao=sessao,
                fornecedor_id=fornecedor_teste.id,
            )

            print("\nFornecedor buscado:")
            print(fornecedor_buscado)

            fornecedor_desativado = desativar_fornecedor(
                sessao=sessao,
                fornecedor_id=fornecedor_teste.id,
            )

            print("\nFornecedor desativado:")
            print(
                fornecedor_desativado.nome,
                fornecedor_desativado.ativo,
            )

            fornecedor_reativado = reativar_fornecedor(
                sessao=sessao,
                fornecedor_id=fornecedor_teste.id,
            )

            print("\nFornecedor reativado:")
            print(
                fornecedor_reativado.nome,
                fornecedor_reativado.ativo,
            )

            assert fornecedor_buscado is not None
            assert fornecedor_atualizado.prazo_entrega_dias == 3
            assert fornecedor_atualizado.cidade == "Taubaté"
            assert fornecedor_reativado.ativo is True

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_fornecedor()