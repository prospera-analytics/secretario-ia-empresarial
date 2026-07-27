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


def testar_busca_web_e_cache() -> None:
    """
    Testa o fluxo completo do serviço sem acessar a internet.

    O teste verifica que:

    1. Sem preço em cache, a busca web simulada é chamada.
    2. O preço é extraído e salvo na sessão.
    3. Uma segunda consulta usa o cache.
    4. A Tavily não é chamada novamente.
    5. O rollback remove todos os dados temporários.
    """

    identificador = uuid4().hex[:8]

    with SessionLocal() as sessao:
        try:
            produto = Produto(
                nome=f"Samsung Galaxy S24 Teste {identificador}",
                categoria="Smartphone",
                marca="Samsung",
                armazenamento_gb=256,
                descricao="Produto temporário para teste.",
                preco_venda=Decimal("5499.90"),
                ativo=True,
            )

            concorrente = Concorrente(
                nome=f"Loja Teste {identificador}",
                dominio=f"loja-teste-{identificador}.com.br",
                ativo=True,
            )

            sessao.add_all(
                [
                    produto,
                    concorrente,
                ]
            )

            sessao.flush()
            sessao.refresh(produto)
            sessao.refresh(concorrente)

            resposta_web_simulada = {
                "titulo": (
                    "Samsung Galaxy S24 Teste "
                    f"{identificador} 256GB por "
                    "R$ 4.999,90 no Pix"
                ),
                "url": (
                    "https://"
                    f"{concorrente.dominio}"
                    "/smartphone-galaxy-s24"
                ),
                "conteudo": (
                    "Oferta disponível por R$ 4.999,90 no Pix "
                    "ou em 10x de R$ 549,99."
                ),
                "pontuacao": 0.91,
            }

            with patch(
                "servicos.busca_precos."
                "buscar_oferta_no_concorrente"
            ) as busca_web_simulada:
                busca_web_simulada.return_value = (
                    resposta_web_simulada
                )

                resultado_web = (
                    consultar_preco_produto_concorrente(
                        sessao=sessao,
                        produto_id=produto.id,
                        concorrente_id=concorrente.id,
                    )
                )

                print("\nResultado da primeira consulta:")
                print(resultado_web)

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
                assert resultado_web.tipo_correspondencia == "exato"
                assert (
                    resultado_web.similaridade
                    == Decimal("1.000")
                )
                assert resultado_web.registro_preco.id is not None

                busca_web_simulada.assert_called_once()

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

                print("\nResultado da segunda consulta:")
                print(resultado_cache)

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

                # Continua sendo apenas uma chamada:
                # a segunda consulta utilizou o cache.
                assert busca_web_simulada.call_count == 1

            print(
                "\nO fluxo web simulada → extração → banco "
                "→ cache funcionou corretamente."
            )

        finally:
            sessao.rollback()

            print(
                "\nRollback executado. "
                "Nenhum dado de teste foi mantido."
            )


if __name__ == "__main__":
    testar_busca_web_e_cache()