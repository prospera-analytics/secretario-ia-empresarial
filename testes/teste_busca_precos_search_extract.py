from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from database.conexao import SessionLocal
from database.models.concorrente import Concorrente
from database.models.produto import Produto
from servicos.busca_precos import consultar_preco_produto_concorrente
from web.tavily import PaginaExtraida


def executar_teste() -> None:
    sessao = SessionLocal()

    try:
        produto = sessao.query(Produto).filter(
            Produto.ativo.is_(True)
        ).first()

        concorrente = sessao.query(Concorrente).filter(
            Concorrente.ativo.is_(True)
        ).first()

        if produto is None or concorrente is None:
            raise RuntimeError(
                "Cadastre ao menos um produto e um concorrente antes do teste."
            )

        armazenamento = produto.armazenamento_gb

        pagina_correta = PaginaExtraida(
            titulo=produto.nome,
            url=(
                f"https://{concorrente.dominio}/produto/"
                f"produto-correto"
            ),
            conteudo_resumo="",
            conteudo_extraido=(
                f"{produto.nome}. "
                f"Oferta por R$ 7.499,90 no Pix. "
                f"Ou 10x de R$ 799,90 sem juros."
            ),
            pontuacao_busca=0.92,
        )

        pagina_ambigua = PaginaExtraida(
            titulo="Celulares em promoção",
            url=(
                f"https://{concorrente.dominio}/categoria/"
                f"celulares"
            ),
            conteudo_resumo="",
            conteudo_extraido=(
                f"{produto.marca} smartphone {armazenamento}GB "
                f"R$ 12.207,80. "
                f"Outro modelo 256GB R$ 8.797,90."
            ),
            pontuacao_busca=0.97,
        )

        with patch(
            "servicos.busca_precos.buscar_e_extrair_paginas",
            return_value=[
                pagina_ambigua,
                pagina_correta,
            ],
        ):
            resultado = consultar_preco_produto_concorrente(
                sessao=sessao,
                produto_id=produto.id,
                concorrente_id=concorrente.id,
                forcar_atualizacao=True,
            )

        assert resultado is not None
        assert resultado.preco == Decimal("7499.90")
        assert resultado.url == pagina_correta.url

        print(
            "Teste Search + Extract + validação local aprovado."
        )
        print(resultado)

    finally:
        sessao.rollback()
        sessao.close()


if __name__ == "__main__":
    executar_teste()
