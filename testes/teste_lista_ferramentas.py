from collections import Counter

from agente.ferramentas import criar_ferramentas


def testar_lista_ferramentas() -> None:
    """Valida o carregamento de todas as ferramentas do agente."""

    ferramentas = criar_ferramentas()

    nomes = [
        ferramenta.name
        for ferramenta in ferramentas
    ]

    print("\nFerramentas carregadas:")

    for indice, nome in enumerate(
        nomes,
        start=1,
    ):
        print(f"{indice:02d}. {nome}")

    assert ferramentas, (
        "Nenhuma ferramenta foi carregada."
    )

    nomes_repetidos = [
        nome
        for nome, quantidade in Counter(nomes).items()
        if quantidade > 1
    ]

    assert not nomes_repetidos, (
        "Existem ferramentas com nomes duplicados: "
        + ", ".join(nomes_repetidos)
    )

    grupos_esperados = {
        "produto",
        "estoque",
        "fornecedor",
        "compra",
        "venda",
        "campanha",
        "concorrente",
    }

    grupos_encontrados: set[str] = set()

    for nome in nomes:
        for grupo in grupos_esperados:
            if grupo in nome:
                grupos_encontrados.add(grupo)

    grupos_ausentes = (
        grupos_esperados - grupos_encontrados
    )

    assert not grupos_ausentes, (
        "Não foram encontradas ferramentas para: "
        + ", ".join(sorted(grupos_ausentes))
    )

    print(
        f"\nTotal de ferramentas carregadas: "
        f"{len(ferramentas)}"
    )

    print(
        "\nTodas as ferramentas foram carregadas "
        "sem nomes duplicados."
    )


if __name__ == "__main__":
    testar_lista_ferramentas()