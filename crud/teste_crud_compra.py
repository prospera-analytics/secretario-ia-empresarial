from datetime import date, timedelta
from decimal import Decimal

from database.conexao import SessionLocal
from database.crud.compra import (
    atualizar_previsao_entrega,
    atualizar_status_compra,
    buscar_compra_por_id,
    cadastrar_compra,
    calcular_valor_total,
    listar_compras,
    listar_compras_pendentes,
)
from database.crud.fornecedor import listar_fornecedores
from database.crud.produto import listar_produtos


def testar_crud_compra() -> None:
    with SessionLocal() as sessao:
        try:
            compras = listar_compras(sessao)

            print("\nCompras cadastradas:")

            for compra in compras:
                print(
                    compra.id,
                    compra.produto.nome,
                    compra.fornecedor.nome,
                    compra.quantidade,
                    compra.status,
                    f"R$ {calcular_valor_total(compra):,.2f}",
                )

            pendentes = listar_compras_pendentes(sessao)

            print("\nCompras pendentes ou enviadas:")

            for compra in pendentes:
                print(
                    compra.produto.nome,
                    compra.status,
                    compra.previsao_entrega,
                )

            produtos = listar_produtos(sessao)
            fornecedores = listar_fornecedores(sessao)

            if not produtos:
                raise RuntimeError(
                    "Nenhum produto encontrado para o teste."
                )

            if not fornecedores:
                raise RuntimeError(
                    "Nenhum fornecedor encontrado para o teste."
                )

            hoje = date.today()

            compra_teste = cadastrar_compra(
                sessao=sessao,
                produto_id=produtos[0].id,
                fornecedor_id=fornecedores[0].id,
                quantidade=5,
                preco_unitario=Decimal("4500.00"),
                data_compra=hoje,
                previsao_entrega=hoje + timedelta(days=3),
                status="pendente",
            )

            print("\nCompra criada:")
            print(compra_teste)

            print("\nValor total:")
            print(f"R$ {calcular_valor_total(compra_teste):,.2f}")

            compra_atualizada = atualizar_status_compra(
                sessao=sessao,
                compra_id=compra_teste.id,
                novo_status="enviado",
            )

            print("\nStatus atualizado:")
            print(compra_atualizada.status)

            nova_previsao = hoje + timedelta(days=5)

            compra_atualizada = atualizar_previsao_entrega(
                sessao=sessao,
                compra_id=compra_teste.id,
                nova_previsao=nova_previsao,
            )

            print("\nNova previsão de entrega:")
            print(compra_atualizada.previsao_entrega)

            compra_buscada = buscar_compra_por_id(
                sessao=sessao,
                compra_id=compra_teste.id,
            )

            assert compra_buscada is not None
            assert compra_buscada.status == "enviado"
            assert compra_buscada.previsao_entrega == nova_previsao
            assert calcular_valor_total(
                compra_buscada
            ) == Decimal("22500.00")

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_compra()