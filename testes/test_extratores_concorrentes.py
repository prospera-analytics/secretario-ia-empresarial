from __future__ import annotations

from decimal import Decimal

from web.concorrentes import extrair_preco_concorrente


def test_extrair_preco_amazon_pix() -> None:
    conteudo = """
    Apple iPhone 16 (128 GB) – Rosa

    R$6.119,10
    à vista no Pix ou NuPay (10% off)

    ou R$6.799,00 em até 12x de R$566,62 sem juros
    """

    resultado = extrair_preco_concorrente(
        dominio="amazon.com.br",
        conteudo=conteudo,
    )

    assert resultado is not None
    assert resultado.valor == Decimal("6119.10")
    assert resultado.modalidade == "avista"


def test_extrair_preco_amazon_total_quando_nao_ha_pix() -> None:
    conteudo = """
    Apple iPhone 16 (128 GB)

    R$6.799,00
    em até 12x de R$566,58 sem juros
    """

    resultado = extrair_preco_concorrente(
        dominio="amazon.com.br",
        conteudo=conteudo,
    )

    assert resultado is not None
    assert resultado.valor == Decimal("6799.00")
    assert resultado.modalidade == "preco_total"


def test_amazon_nao_soma_parcelas() -> None:
    conteudo = """
    Apple iPhone 16 (128 GB)

    em até 12x de R$566,58 sem juros
    """

    resultado = extrair_preco_concorrente(
        dominio="amazon.com.br",
        conteudo=conteudo,
    )

    assert resultado is None


def test_extrair_preco_magalu_pix() -> None:
    conteudo = """
    Smartphone Apple iPhone 16 128GB

    R$ 5.999,00 no Pix
    ou R$ 6.499,00 em 10x de R$ 649,90 sem juros
    """

    resultado = extrair_preco_concorrente(
        dominio="magazineluiza.com.br",
        conteudo=conteudo,
    )

    assert resultado is not None
    assert resultado.valor == Decimal("5999.00")
    assert resultado.modalidade == "avista"


def test_extrair_preco_magalu_total_quando_nao_ha_pix() -> None:
    conteudo = """
    Smartphone Apple iPhone 16 128GB

    R$ 6.499,00
    em 10x de R$ 649,90 sem juros
    """

    resultado = extrair_preco_concorrente(
        dominio="magazineluiza.com.br",
        conteudo=conteudo,
    )

    assert resultado is not None
    assert resultado.valor == Decimal("6499.00")
    assert resultado.modalidade == "preco_total"


def test_dominio_nao_suportado() -> None:
    conteudo = """
    Apple iPhone 16 128GB
    R$ 5.999,00 à vista
    """

    resultado = extrair_preco_concorrente(
        dominio="loja-desconhecida.com.br",
        conteudo=conteudo,
    )

    assert resultado is None


def test_conteudo_sem_preco() -> None:
    conteudo = """
    Apple iPhone 16 128GB

    Produto indisponível no momento.
    """

    resultado = extrair_preco_concorrente(
        dominio="amazon.com.br",
        conteudo=conteudo,
    )

    assert resultado is None