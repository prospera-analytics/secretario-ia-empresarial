from agente.contexto import (
    normalizar_texto,
    resolver_contexto,
)
from agente.memoria import (
    criar_memoria_vazia,
    registrar_concorrente,
    registrar_produto,
)


def test_normalizar_texto() -> None:
    assert (
        normalizar_texto(
            "Preço do iPhone 16 128GB"
        )
        == "preco do iphone 16 128 gb"
    )


def test_resolver_produto_e_amazon() -> None:
    contexto = resolver_contexto(
        "Qual é o preço atual do iPhone 16 128 GB "
        "na Amazon?"
    )

    assert contexto.produto is not None
    assert contexto.produto["id"] == 1
    assert contexto.concorrente is not None
    assert contexto.concorrente["nome"] == "Amazon"


def test_reutilizar_contexto_confirmado() -> None:
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

    contexto = resolver_contexto(
        "Como ele se compara com o nosso produto?",
        memoria=memoria,
    )

    assert contexto.produto is not None
    assert contexto.produto["id"] == 1
    assert contexto.concorrente is not None
    assert contexto.concorrente["id"] == 2
    assert contexto.usou_produto_memoria is True
    assert contexto.usou_concorrente_memoria is True


def test_trocar_apenas_concorrente() -> None:
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

    contexto = resolver_contexto(
        "E na Magazine Luiza?",
        memoria=memoria,
    )

    assert contexto.produto is not None
    assert contexto.produto["id"] == 1
    assert contexto.usou_produto_memoria is True

    assert contexto.concorrente is not None
    assert (
        contexto.concorrente["nome"]
        == "Magazine Luiza"
    )
    assert (
        contexto.usou_concorrente_memoria
        is False
    )