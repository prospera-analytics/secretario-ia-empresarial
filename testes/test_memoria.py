from agente.memoria import (
    criar_memoria_vazia,
    registrar_concorrente,
    registrar_oferta,
    registrar_produto,
)


def test_memoria_inicial_vazia() -> None:
    memoria = criar_memoria_vazia()

    assert memoria["produto"] is None
    assert memoria["concorrente"] is None
    assert memoria["ultima_oferta"] is None
    assert memoria["ultima_comparacao"] is None


def test_memoria_registra_produto_e_concorrente() -> None:
    memoria = criar_memoria_vazia()

    memoria = registrar_produto(
        memoria,
        {
            "id": 1,
            "nome": "Apple iPhone 16 128 GB",
            "marca": "Apple",
            "armazenamento_gb": 128,
            "preco_venda": 6499.90,
            "ativo": True,
        },
    )

    memoria = registrar_concorrente(
        memoria,
        {
            "id": 2,
            "nome": "Amazon",
            "dominio": "amazon.com.br",
            "ativo": True,
        },
    )

    assert memoria["produto"]["id"] == 1
    assert memoria["concorrente"]["id"] == 2


def test_memoria_registra_oferta_real() -> None:
    memoria = criar_memoria_vazia()

    memoria = registrar_oferta(
        memoria,
        {
            "fonte": "web",
            "produto_id": 1,
            "produto_nome": "Apple iPhone 16 128 GB",
            "concorrente_id": 2,
            "concorrente_nome": "Amazon",
            "produto_encontrado": (
                "Apple iPhone 16 (128 GB)"
            ),
            "preco": 5443.33,
            "moeda": "BRL",
            "correspondencia": "equivalente",
            "similaridade": 1.0,
            "url": (
                "https://www.amazon.com.br/"
                "dp/B0DJFSTQHX"
            ),
            "coletado_em": "2026-07-31T22:52:00",
            "diferencas": [],
        },
    )

    oferta = memoria["ultima_oferta"]

    assert oferta["preco"] == 5443.33
    assert oferta["url"].endswith(
        "B0DJFSTQHX"
    )
    assert (
        memoria["ultimo_fluxo"]
        == "consultar_preco_concorrente"
    )