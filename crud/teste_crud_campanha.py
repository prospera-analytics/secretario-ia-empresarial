from datetime import date, timedelta
from decimal import Decimal

from database.conexao import SessionLocal
from database.crud.campanha import (
    adicionar_produto_campanha,
    atualizar_campanha,
    buscar_campanha_por_id,
    cadastrar_campanha,
    calcular_faturamento_campanha,
    calcular_retorno_sobre_investimento,
    listar_campanhas,
    listar_produtos_da_campanha,
)
from database.crud.produto import listar_produtos


def testar_crud_campanha() -> None:
    with SessionLocal() as sessao:
        try:
            campanhas = listar_campanhas(sessao)

            print("\nCampanhas cadastradas:")

            for campanha in campanhas:
                faturamento = calcular_faturamento_campanha(
                    sessao=sessao,
                    campanha_id=campanha.id,
                )

                roi = calcular_retorno_sobre_investimento(
                    sessao=sessao,
                    campanha_id=campanha.id,
                )

                print(
                    campanha.id,
                    campanha.nome,
                    campanha.status,
                    f"faturamento=R$ {faturamento:,.2f}",
                    (
                        f"ROI={roi:.2f}%"
                        if roi is not None
                        else "ROI indisponível"
                    ),
                )

            produtos = listar_produtos(sessao)

            if not produtos:
                raise RuntimeError(
                    "Nenhum produto encontrado para o teste."
                )

            hoje = date.today()

            campanha_teste = cadastrar_campanha(
                sessao=sessao,
                nome="Campanha Temporária de Teste",
                descricao="Campanha criada apenas para teste.",
                canal="Instagram",
                data_inicio=hoje,
                data_fim=hoje + timedelta(days=7),
                investimento=Decimal("1500.00"),
                status="planejada",
            )

            print("\nCampanha criada:")
            print(campanha_teste)

            campanha_atualizada = atualizar_campanha(
                sessao=sessao,
                campanha_id=campanha_teste.id,
                status="ativa",
                investimento=Decimal("1800.00"),
            )

            print("\nCampanha atualizada:")
            print(
                campanha_atualizada.nome,
                campanha_atualizada.status,
                campanha_atualizada.investimento,
            )

            relacionamento = adicionar_produto_campanha(
                sessao=sessao,
                campanha_id=campanha_teste.id,
                produto_id=produtos[0].id,
                desconto_percentual=Decimal("10.00"),
            )

            print("\nProduto adicionado à campanha:")
            print(
                relacionamento.produto_id,
                relacionamento.desconto_percentual,
            )

            produtos_campanha = listar_produtos_da_campanha(
                sessao=sessao,
                campanha_id=campanha_teste.id,
            )

            print("\nProdutos da campanha:")

            for item in produtos_campanha:
                print(
                    item.produto.nome,
                    f"{item.desconto_percentual}% de desconto",
                )

            campanha_buscada = buscar_campanha_por_id(
                sessao=sessao,
                campanha_id=campanha_teste.id,
            )

            assert campanha_buscada is not None
            assert campanha_buscada.status == "ativa"
            assert campanha_buscada.investimento == Decimal(
                "1800.00"
            )
            assert len(produtos_campanha) == 1

            sessao.rollback()

            print("\nTeste concluído com sucesso.")

        except Exception:
            sessao.rollback()
            raise


if __name__ == "__main__":
    testar_crud_campanha()