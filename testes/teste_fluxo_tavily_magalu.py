from __future__ import annotations

from servicos.extracao_precos import (
    OfertaValidada,
    analisar_oferta_produto,
)
from web.tavily import (
    PaginaExtraida,
    buscar_e_extrair_paginas,
)


NOME_PRODUTO_BUSCA = "Apple iPhone 16 128GB"
NOME_PRODUTO_CADASTRADO = "iPhone 16"
MARCA = "Apple"
ARMAZENAMENTO_GB = 128

# NOME_CONCORRENTE = "Magazine Luiza"
# DOMINIO_CONCORRENTE = "magazineluiza.com.br"

NOME_CONCORRENTE = "Amazon"
DOMINIO_CONCORRENTE = "amazon.com.br"


def executar_teste() -> None:
    print("=" * 100)
    print("TESTE INTEGRADO — SEARCH + EXTRACT + VALIDAÇÃO DE OFERTA")
    print("=" * 100)

    paginas = buscar_e_extrair_paginas(
        nome_produto=NOME_PRODUTO_BUSCA,
        nome_concorrente=NOME_CONCORRENTE,
        dominio_concorrente=DOMINIO_CONCORRENTE,
    )

    print()
    print(
        "Quantidade de páginas úteis extraídas:",
        len(paginas),
    )

    if not paginas:
        print()
        print(
            "Nenhuma página útil foi obtida. "
            "Verifique os resultados da Tavily Search."
        )
        return

    ofertas_reconhecidas: list[
        tuple[
            PaginaExtraida,
            OfertaValidada,
        ]
    ] = []

    for indice, pagina in enumerate(
        paginas,
        start=1,
    ):
        print()
        print("-" * 100)
        print(f"PÁGINA {indice}")
        print("-" * 100)

        print("Título da busca:")
        print(pagina.titulo)

        print()
        print("URL:")
        print(pagina.url)

        print()
        print(
            "Pontuação da busca:",
            pagina.pontuacao_busca,
        )

        conteudo = pagina.conteudo_extraido or ""

        print()
        print(
            "Tamanho do conteúdo:",
            len(conteudo),
        )

        print()
        print("Trecho inicial:")
        print(conteudo[:1000])

        oferta = analisar_oferta_produto(
            dominio=DOMINIO_CONCORRENTE,
            titulo=pagina.titulo,
            conteudo=conteudo,
            nome_produto=NOME_PRODUTO_CADASTRADO,
            marca=MARCA,
            armazenamento_gb=ARMAZENAMENTO_GB,
        )

        print()

        if oferta is None:
            print("Oferta reconhecida: não")
            continue

        ofertas_reconhecidas.append(
            (
                pagina,
                oferta,
            )
        )

        print("Oferta reconhecida: sim")

        print()
        print("OFERTA VALIDADA")

        print(
            "Preço:",
            oferta.preco,
        )

        print(
            "Moeda:",
            oferta.moeda,
        )

        print(
            "Modalidade:",
            oferta.modalidade,
        )

        print(
            "Correspondência:",
            oferta.correspondencia,
        )

        print(
            "Confiança:",
            oferta.confianca,
        )

        print(
            "Diferenças:",
            oferta.diferencas,
        )

    print()
    print("=" * 100)
    print("RESUMO")
    print("=" * 100)

    print(
        "Páginas úteis:",
        len(paginas),
    )

    print(
        "Total de ofertas reconhecidas:",
        len(ofertas_reconhecidas),
    )

    if not ofertas_reconhecidas:
        print()
        print(
            "As páginas foram extraídas, mas nenhuma oferta "
            "válida foi reconhecida."
        )
        return

    print()
    print("TODAS AS OFERTAS RECONHECIDAS:")

    for pagina, oferta in ofertas_reconhecidas:
        print()
        print("-" * 100)

        print(
            "Preço:",
            oferta.preco,
        )

        print(
            "Modalidade:",
            oferta.modalidade,
        )

        print(
            "URL:",
            pagina.url,
        )

        print(
            "Correspondência:",
            oferta.correspondencia,
        )

        print(
            "Confiança:",
            oferta.confianca,
        )

        print(
            "Pontuação da busca:",
            pagina.pontuacao_busca,
        )

        print(
            "Diferenças:",
            oferta.diferencas,
        )

    ordem_correspondencia = {
        "exato": 4,
        "equivalente": 3,
        "muito_similar": 2,
        "similar": 1,
    }

    melhor_pagina, melhor_oferta = max(
        ofertas_reconhecidas,
        key=lambda item: (
            ordem_correspondencia[
                item[1].correspondencia
            ],
            item[1].confianca,
            item[0].pontuacao_busca,
            -item[1].preco,
        ),
    )

    print()
    print("=" * 100)
    print("MELHOR OFERTA SELECIONADA")
    print("=" * 100)

    print(
        "Título:",
        melhor_pagina.titulo,
    )

    print(
        "Preço:",
        melhor_oferta.preco,
    )

    print(
        "Moeda:",
        melhor_oferta.moeda,
    )

    print(
        "Modalidade:",
        melhor_oferta.modalidade,
    )

    print(
        "URL:",
        melhor_pagina.url,
    )

    print(
        "Correspondência:",
        melhor_oferta.correspondencia,
    )

    print(
        "Confiança:",
        melhor_oferta.confianca,
    )

    print(
        "Pontuação da busca:",
        melhor_pagina.pontuacao_busca,
    )

    print(
        "Diferenças:",
        melhor_oferta.diferencas,
    )


if __name__ == "__main__":
    executar_teste()