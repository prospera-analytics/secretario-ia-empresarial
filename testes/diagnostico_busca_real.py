from database.conexao import SessionLocal
from database.models.produto import Produto
from database.models.concorrente import Concorrente

from web.tavily import (
    buscar_paginas_candidatas,
    extrair_paginas_candidatas,
)

from servicos.extracao_precos import analisar_oferta_produto


def main():
    sessao = SessionLocal()

    try:
        produto = sessao.get(Produto, 1)
        concorrente = sessao.get(Concorrente, 1)

        print("=" * 80)
        print("PRODUTO")
        print(produto.nome)
        print()

        candidatos = buscar_paginas_candidatas(
            nome_produto=produto.nome,
            nome_concorrente=concorrente.nome,
            dominio_concorrente=concorrente.dominio,
        )

        print("RESULTADOS SEARCH:", len(candidatos))

        for i, candidato in enumerate(candidatos, 1):
            print()
            print("-" * 80)
            print(f"SEARCH {i}")
            print("Título:", candidato.titulo)
            print("URL:", candidato.url)
            print("Score:", candidato.pontuacao)

        paginas = extrair_paginas_candidatas(
            candidatos,
            produto.nome,
        )

        print()
        print("=" * 80)
        print("PÁGINAS EXTRAÍDAS:", len(paginas))

        for i, pagina in enumerate(paginas, 1):

            print()
            print("=" * 80)
            print(f"PÁGINA {i}")
            print("Título:", pagina.titulo)
            print("URL:", pagina.url)

            ofertas = analisar_oferta_produto(
                titulo=pagina.titulo,
                conteudo=pagina.conteudo_extraido,
                nome_produto=produto.nome,
                marca=produto.marca,
                armazenamento_gb=produto.armazenamento_gb,
            )

            print("Ofertas encontradas:", len(ofertas))

            if oferta is not None:
                print(oferta)

            print()
            print("INÍCIO DO CONTEÚDO:")
            print(pagina.conteudo_extraido[:1500])

    finally:
        sessao.close()


if __name__ == "__main__":
    main()