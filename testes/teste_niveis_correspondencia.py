from decimal import Decimal

from servicos.extracao_precos import analisar_oferta_produto


def melhor(titulo: str, conteudo: str):
    ofertas = analisar_oferta_produto(
        titulo=titulo,
        conteudo=conteudo,
        nome_produto="Apple iPhone 16 128 GB",
        marca="Apple",
        armazenamento_gb=128,
    )
    assert ofertas, f"Nenhuma oferta retornada para: {titulo}"
    return ofertas[0]


def executar_teste() -> None:
    equivalente = melhor(
        "Apple iPhone 16 128GB Azul 5G",
        "Apple iPhone 16 128GB Azul. Por R$ 6.499,90 no Pix.",
    )
    assert equivalente.preco == Decimal("6499.90")
    assert equivalente.correspondencia in {"exato", "equivalente"}

    armazenamento = melhor(
        "Apple iPhone 16 256GB Preto",
        "Apple iPhone 16 256GB Preto. Por R$ 7.199,90 no Pix.",
    )
    assert armazenamento.correspondencia == "muito_similar"
    assert any("armazenamento" in d for d in armazenamento.diferencas)

    variante = melhor(
        "Apple iPhone 16 Plus 128GB Verde",
        "Apple iPhone 16 Plus 128GB Verde. Por R$ 8.212,09 no Pix.",
    )
    assert variante.correspondencia == "muito_similar"
    assert any("variante" in d for d in variante.diferencas)

    usado = melhor(
        "Usado: Apple iPhone 16 128GB Rosa",
        "Usado Apple iPhone 16 128GB Rosa. Por R$ 4.629,90.",
    )
    assert usado.correspondencia == "similar"
    assert any("usado" in d for d in usado.diferencas)

    print("Teste dos níveis de correspondência aprovado.")


if __name__ == "__main__":
    executar_teste()
