from types import SimpleNamespace
from decimal import Decimal

from agente.memoria import (
    criar_memoria_vazia,
    registrar_concorrente,
    registrar_produto,
)
from agente.orquestrador import (
    detectar_fluxo,
    executar_fluxo_deterministico,
)


def test_detectar_listagem_produtos() -> None:
    assert (
        detectar_fluxo(
            "Liste os nossos produtos"
        )
        == "listar_produtos"
    )


def test_detectar_consulta_preco_concorrente() -> None:
    from agente.contexto import resolver_contexto

    contexto = resolver_contexto(
        "Qual é o preço do iPhone 16 128 GB "
        "na Amazon?"
    )

    assert (
        detectar_fluxo(
            (
                "Qual é o preço do iPhone 16 "
                "128 GB na Amazon?"
            ),
            contexto=contexto,
        )
        == "consultar_preco_concorrente"
    )


def test_listar_produtos_sem_llm() -> None:
    resultado = executar_fluxo_deterministico(
        pergunta="Liste os nossos produtos",
        memoria=criar_memoria_vazia(),
    )

    assert resultado.tratado is True
    assert resultado.fluxo == "listar_produtos"
    assert resultado.dados is not None
    assert resultado.dados["quantidade"] > 0
    assert "Apple iPhone 16" in resultado.resposta


def test_detectar_preco_interno() -> None:
    from agente.contexto import resolver_contexto

    contexto = resolver_contexto(
        "Qual é nosso preço do iPhone 16 128 GB?"
    )

    assert (
        detectar_fluxo(
            (
                "Qual é nosso preço do "
                "iPhone 16 128 GB?"
            ),
            contexto=contexto,
        )
        == "consultar_preco_interno"
    )


def test_detectar_comparacao_catalogo() -> None:
    from agente.contexto import resolver_contexto

    pergunta = (
        "Como nossos preços se comparam "
        "aos concorrentes?"
    )

    contexto = resolver_contexto(
        pergunta
    )

    assert (
        detectar_fluxo(
            pergunta,
            contexto=contexto,
        )
        == "comparar_catalogo_concorrentes"
    )


def test_detectar_produtos_equivalentes() -> None:
    from agente.contexto import resolver_contexto

    pergunta = (
        "Quais produtos em comum ou equivalentes "
        "temos com a Magazine Luiza?"
    )

    contexto = resolver_contexto(
        pergunta
    )

    assert (
        detectar_fluxo(
            pergunta,
            contexto=contexto,
        )
        == "listar_produtos_equivalentes"
    )


def test_consultar_preco_interno_sem_llm() -> None:
    resultado = executar_fluxo_deterministico(
        pergunta=(
            "Qual é nosso preço do "
            "iPhone 16 128 GB?"
        ),
        memoria=criar_memoria_vazia(),
    )

    assert resultado.tratado is True
    assert (
        resultado.fluxo
        == "consultar_preco_interno"
    )
    assert "R$ 6.499,90" in resultado.resposta

def test_comparar_usando_memoria(
    monkeypatch,
) -> None:
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

    resultado_servico = SimpleNamespace(
        fonte="cache",
        produto_id=1,
        produto_nome="Apple iPhone 16 128 GB",
        concorrente_id=2,
        concorrente_nome="Amazon",
        titulo_encontrado=(
            "Apple iPhone 16 (128 GB)"
        ),
        preco=Decimal("5443.33"),
        moeda="BRL",
        tipo_correspondencia="equivalente",
        similaridade=Decimal("1.000"),
        url=(
            "https://www.amazon.com.br/"
            "dp/B0DJFSTQHX"
        ),
        coletado_em=None,
        diferencas=(),
    )

    monkeypatch.setattr(
        (
            "agente.orquestrador."
            "consultar_preco_produto_concorrente"
        ),
        lambda **kwargs: resultado_servico,
    )

    resultado = executar_fluxo_deterministico(
        pergunta=(
            "Como ele se compara com o "
            "nosso produto?"
        ),
        memoria=memoria,
    )

    assert resultado.tratado is True
    assert (
        resultado.fluxo
        == "comparar_preco_concorrente"
    )
    assert "R$ 6.499,90" in resultado.resposta
    assert "R$ 5.443,33" in resultado.resposta
    assert "B0DJFSTQHX" in resultado.resposta
    assert (
        resultado.memoria["ultima_comparacao"]
        is not None
    )