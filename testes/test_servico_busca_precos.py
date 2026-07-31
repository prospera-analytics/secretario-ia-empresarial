from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select

from database.conexao import SessionLocal
from database.models.concorrente import Concorrente
from database.models.preco_concorrente import PrecoConcorrente
from database.models.produto import Produto
from servicos.busca_precos import (
    consultar_preco_produto_concorrente,
)
from servicos.extracao_precos import OfertaValidada
from web.tavily import PaginaExtraida


def test_busca_web_salva_no_banco_e_utiliza_cache() -> None:
    """
    Verifica o fluxo principal do serviço:

    página extraída
        → oferta validada
        → registro no banco
        → consulta posterior pelo cache
    """

    identificador = uuid4().hex[:8]

    with SessionLocal() as sessao:
        try:
            produto = Produto(
                nome=(
                    f"Samsung Galaxy S24 "
                    f"Teste {identificador}"
                ),
                categoria="Smartphone",
                marca="Samsung",
                armazenamento_gb=256,
                descricao=(
                    "Produto temporário para teste."
                ),
                preco_venda=Decimal("5499.90"),
                ativo=True,
            )

            concorrente = Concorrente(
                nome=f"Amazon Teste {identificador}",
                dominio=(
                    f"teste-{identificador}."
                    "amazon.com.br"
                ),
                ativo=True,
            )

            sessao.add_all([produto, concorrente])
            sessao.flush()

            pagina_simulada = PaginaExtraida(
                titulo=(
                    f"Samsung Galaxy S24 Teste "
                    f"{identificador} 256GB"
                ),
                url=(
                    "https://www.amazon.com.br/"
                    f"galaxy-s24-{identificador}"
                ),
                conteudo_resumo=(
                    "Samsung Galaxy S24 256GB"
                ),
                conteudo_extraido=(
                    "Samsung Galaxy S24 256GB. "
                    "Preço à vista: R$ 4.999,90."
                ),
                pontuacao_busca=0.91,
            )

            oferta_simulada = OfertaValidada(
                preco=Decimal("4999.90"),
                moeda="BRL",
                modalidade="avista",
                correspondencia="exato",
                confianca=Decimal("1.000"),
                diferencas=(),
            )

            with (
                patch(
                    "servicos.busca_precos."
                    "buscar_e_extrair_paginas",
                    return_value=[pagina_simulada],
                ) as busca_web_simulada,
                patch(
                    "servicos.busca_precos."
                    "analisar_oferta_produto",
                    return_value=oferta_simulada,
                ) as analise_simulada,
            ):
                resultado_web = (
                    consultar_preco_produto_concorrente(
                        sessao=sessao,
                        produto_id=produto.id,
                        concorrente_id=concorrente.id,
                    )
                )

                assert resultado_web is not None
                assert resultado_web.fonte == "web"
                assert resultado_web.produto_id == produto.id
                assert (
                    resultado_web.concorrente_id
                    == concorrente.id
                )
                assert (
                    resultado_web.preco
                    == Decimal("4999.90")
                )
                assert resultado_web.moeda == "BRL"
                assert (
                    resultado_web.tipo_correspondencia
                    == "exato"
                )
                assert (
                    resultado_web.similaridade
                    == Decimal("1.000")
                )
                assert (
                    resultado_web.registro_preco.id
                    is not None
                )

                busca_web_simulada.assert_called_once()
                analise_simulada.assert_called_once()

                registros = list(
                    sessao.scalars(
                        select(PrecoConcorrente).where(
                            PrecoConcorrente.produto_id
                            == produto.id,
                            PrecoConcorrente.concorrente_id
                            == concorrente.id,
                        )
                    ).all()
                )

                assert len(registros) == 1
                assert (
                    registros[0].preco
                    == Decimal("4999.90")
                )

                resultado_cache = (
                    consultar_preco_produto_concorrente(
                        sessao=sessao,
                        produto_id=produto.id,
                        concorrente_id=concorrente.id,
                    )
                )

                assert resultado_cache is not None
                assert resultado_cache.fonte == "cache"
                assert (
                    resultado_cache.preco
                    == Decimal("4999.90")
                )
                assert (
                    resultado_cache.registro_preco.id
                    == resultado_web.registro_preco.id
                )

                # A segunda consulta deve usar o banco,
                # sem repetir a busca ou a análise.
                assert busca_web_simulada.call_count == 1
                assert analise_simulada.call_count == 1

        finally:
            sessao.rollback()