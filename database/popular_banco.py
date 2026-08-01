from argparse import ArgumentParser
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.conexao import SessionLocal
from database.models import (
    Campanha,
    CampanhaProduto,
    Compra,
    Concorrente,
    Estoque,
    Fornecedor,
    PrecoConcorrente,
    Produto,
    Venda,
)



def limpar_dados(sessao: Session) -> None:
    """
    Remove os registros existentes.

    A ordem respeita as dependências entre as tabelas e suas
    respectivas chaves estrangeiras.
    """

    modelos = (
        PrecoConcorrente,
        Concorrente,
        Venda,
        CampanhaProduto,
        Campanha,
        Compra,
        Estoque,
        Produto,
        Fornecedor,
    )

    for modelo in modelos:
        sessao.execute(delete(modelo))


def criar_fornecedores() -> list[Fornecedor]:
    """Cria os fornecedores demonstrativos."""

    return [
        Fornecedor(
            nome="Ingram Micro Brasil",
            cidade="Barueri",
            estado="SP",
            prazo_entrega_dias=2,
        ),
        Fornecedor(
            nome="Agis Distribuição",
            cidade="Campinas",
            estado="SP",
            prazo_entrega_dias=3,
        ),
        Fornecedor(
            nome="SND Distribuição",
            cidade="Barueri",
            estado="SP",
            prazo_entrega_dias=2,
        ),
        Fornecedor(
            nome="All Nations",
            cidade="Serra",
            estado="ES",
            prazo_entrega_dias=6,
        ),
        Fornecedor(
            nome="Officer Distribuidora",
            cidade="Curitiba",
            estado="PR",
            prazo_entrega_dias=5,
        ),
    ]


def criar_produtos() -> list[Produto]:
    """
    Cria o catálogo demonstrativo de smartphones.

    Os preços são simulados e representam os preços internos
    da empresa fictícia.
    """

    return [
        Produto(
            nome="Apple iPhone 16 128 GB",
            categoria="Smartphone",
            marca="Apple",
            armazenamento_gb=128,
            descricao="Smartphone Apple com armazenamento de 128 GB.",
            preco_venda=Decimal("6499.90"),
        ),
        Produto(
            nome="Apple iPhone 16 Pro 256 GB",
            categoria="Smartphone",
            marca="Apple",
            armazenamento_gb=256,
            descricao="Smartphone premium Apple com armazenamento de 256 GB.",
            preco_venda=Decimal("9299.90"),
        ),
        Produto(
            nome="Samsung Galaxy S25 256 GB",
            categoria="Smartphone",
            marca="Samsung",
            armazenamento_gb=256,
            descricao="Smartphone Samsung da linha Galaxy S.",
            preco_venda=Decimal("5999.90"),
        ),
        Produto(
            nome="Samsung Galaxy S25 Ultra 512 GB",
            categoria="Smartphone",
            marca="Samsung",
            armazenamento_gb=512,
            descricao="Smartphone premium Samsung com armazenamento de 512 GB.",
            preco_venda=Decimal("9999.90"),
        ),
        Produto(
            nome="Samsung Galaxy A56 256 GB",
            categoria="Smartphone",
            marca="Samsung",
            armazenamento_gb=256,
            descricao="Smartphone Samsung intermediário.",
            preco_venda=Decimal("2999.90"),
        ),
        Produto(
            nome="Motorola Edge 60 Pro 256 GB",
            categoria="Smartphone",
            marca="Motorola",
            armazenamento_gb=256,
            descricao="Smartphone Motorola da linha Edge.",
            preco_venda=Decimal("3999.90"),
        ),
        Produto(
            nome="Motorola Moto G75 256 GB",
            categoria="Smartphone",
            marca="Motorola",
            armazenamento_gb=256,
            descricao="Smartphone Motorola intermediário.",
            preco_venda=Decimal("2299.90"),
        ),
        Produto(
            nome="Xiaomi 15 512 GB",
            categoria="Smartphone",
            marca="Xiaomi",
            armazenamento_gb=512,
            descricao="Smartphone Xiaomi de alto desempenho.",
            preco_venda=Decimal("6999.90"),
        ),
        Produto(
            nome="Redmi Note 14 Pro 256 GB",
            categoria="Smartphone",
            marca="Xiaomi",
            armazenamento_gb=256,
            descricao="Smartphone intermediário da linha Redmi Note.",
            preco_venda=Decimal("2799.90"),
        ),
        Produto(
            nome="ASUS ROG Phone 9 512 GB",
            categoria="Smartphone",
            marca="ASUS",
            armazenamento_gb=512,
            descricao="Smartphone voltado para jogos e alto desempenho.",
            preco_venda=Decimal("8499.90"),
        ),
    ]


def criar_estoques(produtos: list[Produto]) -> list[Estoque]:
    """Cria um registro de estoque para cada produto."""

    return [
        Estoque(
            produto_id=produtos[0].id,
            quantidade_atual=7,
            estoque_minimo=5,
        ),
        Estoque(
            produto_id=produtos[1].id,
            quantidade_atual=3,
            estoque_minimo=4,
        ),
        Estoque(
            produto_id=produtos[2].id,
            quantidade_atual=11,
            estoque_minimo=6,
        ),
        Estoque(
            produto_id=produtos[3].id,
            quantidade_atual=2,
            estoque_minimo=4,
        ),
        Estoque(
            produto_id=produtos[4].id,
            quantidade_atual=25,
            estoque_minimo=10,
        ),
        Estoque(
            produto_id=produtos[5].id,
            quantidade_atual=6,
            estoque_minimo=7,
        ),
        Estoque(
            produto_id=produtos[6].id,
            quantidade_atual=18,
            estoque_minimo=8,
        ),
        Estoque(
            produto_id=produtos[7].id,
            quantidade_atual=5,
            estoque_minimo=5,
        ),
        Estoque(
            produto_id=produtos[8].id,
            quantidade_atual=22,
            estoque_minimo=10,
        ),
        Estoque(
            produto_id=produtos[9].id,
            quantidade_atual=3,
            estoque_minimo=3,
        ),
    ]


def criar_compras(
    produtos: list[Produto],
    fornecedores: list[Fornecedor],
) -> list[Compra]:
    """Cria compras históricas e compras ainda pendentes."""

    return [
        Compra(
            produto_id=produtos[0].id,
            fornecedor_id=fornecedores[0].id,
            quantidade=15,
            preco_unitario=Decimal("5200.00"),
            data_compra=date(2026, 6, 5),
            previsao_entrega=date(2026, 6, 7),
            status="entregue",
        ),
        Compra(
            produto_id=produtos[1].id,
            fornecedor_id=fornecedores[2].id,
            quantidade=8,
            preco_unitario=Decimal("7600.00"),
            data_compra=date(2026, 6, 10),
            previsao_entrega=date(2026, 6, 12),
            status="entregue",
        ),
        Compra(
            produto_id=produtos[2].id,
            fornecedor_id=fornecedores[1].id,
            quantidade=20,
            preco_unitario=Decimal("4600.00"),
            data_compra=date(2026, 6, 15),
            previsao_entrega=date(2026, 6, 18),
            status="entregue",
        ),
        Compra(
            produto_id=produtos[3].id,
            fornecedor_id=fornecedores[0].id,
            quantidade=10,
            preco_unitario=Decimal("8100.00"),
            data_compra=date(2026, 7, 21),
            previsao_entrega=date(2026, 7, 23),
            status="pendente",
        ),
        Compra(
            produto_id=produtos[4].id,
            fornecedor_id=fornecedores[1].id,
            quantidade=30,
            preco_unitario=Decimal("2150.00"),
            data_compra=date(2026, 6, 20),
            previsao_entrega=date(2026, 6, 23),
            status="entregue",
        ),
        Compra(
            produto_id=produtos[5].id,
            fornecedor_id=fornecedores[2].id,
            quantidade=15,
            preco_unitario=Decimal("3050.00"),
            data_compra=date(2026, 7, 20),
            previsao_entrega=date(2026, 7, 22),
            status="pendente",
        ),
        Compra(
            produto_id=produtos[7].id,
            fornecedor_id=fornecedores[3].id,
            quantidade=10,
            preco_unitario=Decimal("5500.00"),
            data_compra=date(2026, 6, 25),
            previsao_entrega=date(2026, 7, 1),
            status="entregue",
        ),
        Compra(
            produto_id=produtos[9].id,
            fornecedor_id=fornecedores[4].id,
            quantidade=6,
            preco_unitario=Decimal("6900.00"),
            data_compra=date(2026, 7, 22),
            previsao_entrega=date(2026, 7, 27),
            status="pendente",
        ),
    ]


def criar_campanhas() -> list[Campanha]:
    """Cria campanhas promocionais demonstrativas."""

    return [
        Campanha(
            nome="Semana dos Smartphones",
            descricao="Campanha promocional para smartphones premium.",
            canal="Google Ads",
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 7),
            investimento=Decimal("5000.00"),
            status="finalizada",
        ),
        Campanha(
            nome="Festival Android",
            descricao="Campanha para smartphones Android intermediários.",
            canal="Instagram",
            data_inicio=date(2026, 7, 15),
            data_fim=date(2026, 7, 21),
            investimento=Decimal("3500.00"),
            status="finalizada",
        ),
    ]


def criar_campanhas_produtos(
    campanhas: list[Campanha],
    produtos: list[Produto],
) -> list[CampanhaProduto]:
    """Relaciona produtos às campanhas e define seus descontos."""

    return [
        CampanhaProduto(
            campanha_id=campanhas[0].id,
            produto_id=produtos[0].id,
            desconto_percentual=Decimal("8.00"),
        ),
        CampanhaProduto(
            campanha_id=campanhas[0].id,
            produto_id=produtos[1].id,
            desconto_percentual=Decimal("7.00"),
        ),
        CampanhaProduto(
            campanha_id=campanhas[0].id,
            produto_id=produtos[3].id,
            desconto_percentual=Decimal("10.00"),
        ),
        CampanhaProduto(
            campanha_id=campanhas[1].id,
            produto_id=produtos[4].id,
            desconto_percentual=Decimal("12.00"),
        ),
        CampanhaProduto(
            campanha_id=campanhas[1].id,
            produto_id=produtos[5].id,
            desconto_percentual=Decimal("10.00"),
        ),
        CampanhaProduto(
            campanha_id=campanhas[1].id,
            produto_id=produtos[8].id,
            desconto_percentual=Decimal("9.00"),
        ),
    ]


def criar_vendas(
    produtos: list[Produto],
    campanhas: list[Campanha],
) -> list[Venda]:
    """Cria vendas com e sem participação em campanhas."""

    return [
        Venda(
            produto_id=produtos[0].id,
            campanha_id=campanhas[0].id,
            quantidade=4,
            preco_unitario=Decimal("5979.91"),
            data_venda=date(2026, 7, 2),
        ),
        Venda(
            produto_id=produtos[1].id,
            campanha_id=campanhas[0].id,
            quantidade=2,
            preco_unitario=Decimal("8648.91"),
            data_venda=date(2026, 7, 3),
        ),
        Venda(
            produto_id=produtos[3].id,
            campanha_id=campanhas[0].id,
            quantidade=5,
            preco_unitario=Decimal("8999.91"),
            data_venda=date(2026, 7, 5),
        ),
        Venda(
            produto_id=produtos[4].id,
            campanha_id=campanhas[1].id,
            quantidade=10,
            preco_unitario=Decimal("2639.91"),
            data_venda=date(2026, 7, 16),
        ),
        Venda(
            produto_id=produtos[5].id,
            campanha_id=campanhas[1].id,
            quantidade=7,
            preco_unitario=Decimal("3599.91"),
            data_venda=date(2026, 7, 17),
        ),
        Venda(
            produto_id=produtos[8].id,
            campanha_id=campanhas[1].id,
            quantidade=9,
            preco_unitario=Decimal("2547.91"),
            data_venda=date(2026, 7, 18),
        ),
        Venda(
            produto_id=produtos[2].id,
            campanha_id=None,
            quantidade=3,
            preco_unitario=Decimal("5999.90"),
            data_venda=date(2026, 7, 8),
        ),
        Venda(
            produto_id=produtos[6].id,
            campanha_id=None,
            quantidade=6,
            preco_unitario=Decimal("2299.90"),
            data_venda=date(2026, 7, 10),
        ),
        Venda(
            produto_id=produtos[7].id,
            campanha_id=None,
            quantidade=2,
            preco_unitario=Decimal("6999.90"),
            data_venda=date(2026, 7, 12),
        ),
        Venda(
            produto_id=produtos[9].id,
            campanha_id=None,
            quantidade=1,
            preco_unitario=Decimal("8499.90"),
            data_venda=date(2026, 7, 20),
        ),
    ]

def criar_concorrentes() -> list[Concorrente]:
    """
    Cria os concorrentes suportados pela aplicação.
    """

    return [
        Concorrente(
            nome="Magazine Luiza",
            dominio="magazineluiza.com.br",
            ativo=True,
        ),
        Concorrente(
            nome="Amazon",
            dominio="amazon.com.br",
            ativo=True,
        ),
    ]


def popular_banco(limpar: bool = False) -> None:
    """Popula o banco com dados internos demonstrativos."""

    with SessionLocal() as sessao:
        try:
            existe_produto = sessao.scalar(
                select(Produto.id).limit(1)
            )

            if existe_produto and not limpar:
                print(
                    "O banco já possui dados. "
                    "Use --limpar para recriar os registros."
                )
                return

            if limpar:
                limpar_dados(sessao)
                sessao.flush()

            fornecedores = criar_fornecedores()
            produtos = criar_produtos()
            concorrentes = criar_concorrentes()

            sessao.add_all(fornecedores)
            sessao.add_all(produtos)
            sessao.add_all(concorrentes)
            sessao.flush()

            estoques = criar_estoques(produtos)
            compras = criar_compras(produtos, fornecedores)
            campanhas = criar_campanhas()

            sessao.add_all(estoques)
            sessao.add_all(compras)
            sessao.add_all(campanhas)
            sessao.flush()

            campanhas_produtos = criar_campanhas_produtos(
                campanhas,
                produtos,
            )

            vendas = criar_vendas(
                produtos,
                campanhas,
            )

            sessao.add_all(campanhas_produtos)
            sessao.add_all(vendas)
            sessao.commit()

            print("Banco populado com sucesso.")
            print(f"Produtos cadastrados: {len(produtos)}")
            print(f"Fornecedores cadastrados: {len(fornecedores)}")
            print(f"Compras cadastradas: {len(compras)}")
            print(f"Vendas cadastradas: {len(vendas)}")
            print(f"Campanhas cadastradas: {len(campanhas)}")
            print(
                f"Concorrentes cadastrados: {len(concorrentes)}"
            )

            print(
                "As ofertas concorrentes permanecem vazias "
                "até a coleta de dados reais da web."
            )

        except Exception:
            sessao.rollback()
            raise
            

def obter_argumentos():
    """Lê os argumentos fornecidos pelo terminal."""

    parser = ArgumentParser(
        description="Popula o banco com dados demonstrativos."
    )

    parser.add_argument(
        "--limpar",
        action="store_true",
        help="Apaga os registros existentes antes de popular o banco.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    argumentos = obter_argumentos()
    popular_banco(limpar=argumentos.limpar)