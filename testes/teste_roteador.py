"""
Testes do roteador seletivo de ferramentas.

Execute com:

python -m testes.teste_roteador
"""

from agente.ferramentas import criar_ferramentas
from agente.roteador import (
    LIMITE_FERRAMENTAS_POR_REQUISICAO,
    diagnosticar_roteamento,
    rotear_ferramentas,
)


def testar_diagnostico_empresarial() -> None:
    """Diagnóstico deve usar somente ferramentas analíticas."""

    resultado = rotear_ferramentas(
        "Quais são os principais alertas e riscos da empresa?"
    )

    assert resultado.intencao == "analise"
    assert "analises" in resultado.categorias
    assert resultado.ferramentas

    assert all(
        ferramenta.name
        in {
            "analisar_desconto_produto",
            "analisar_descontos_todos_produtos",
            "analisar_risco_estoque_produto",
            "consultar_alertas_estoque",
            "recomendar_fornecedor_para_reposicao",
            "consultar_alertas_produto",
            "consultar_painel_alertas_empresariais",
        }
        for ferramenta in resultado.ferramentas
    )

    print(
        "[OK] Diagnóstico enviado para análises."
    )


def testar_registro_venda() -> None:
    perguntas = [
        "Registre uma venda de duas unidades do produto 1.",
        "Registre uma venda do produto 1.",
    ]

    for pergunta in perguntas:
        resultado = rotear_ferramentas(pergunta)
        nomes = resultado.nomes_ferramentas

        assert resultado.intencao == "escrita"
        assert "venda" in resultado.categorias
        assert "produto" in resultado.categorias
        assert "estoque" in resultado.categorias
        assert "campanha" not in resultado.categorias

        assert "registrar_nova_venda" in nomes

        assert "criar_produto" not in nomes
        assert "criar_estoque_produto" not in nomes
        assert "adicionar_unidades_estoque" not in nomes

    print("[OK] Venda enviada para os grupos corretos.")

def testar_compra() -> None:
    """
    Compra deve receber compra, produto, fornecedor e estoque.
    """

    resultado = rotear_ferramentas(
        "Registre uma compra de 10 unidades com o fornecedor 2."
    )

    assert resultado.intencao == "escrita"
    assert "compra" in resultado.categorias
    assert "produto" in resultado.categorias
    assert "fornecedor" in resultado.categorias
    assert "estoque" in resultado.categorias

    print(
        "[OK] Compra recebeu suas dependências."
    )


def testar_consulta_concorrente() -> None:
    """Consulta de preço deve incluir concorrência."""

    resultado = rotear_ferramentas(
        "Liste os preços dos concorrentes para o produto 3."
    )

    assert resultado.intencao == "leitura"
    assert (
        "preco_concorrente"
        in resultado.categorias
        or "concorrente"
        in resultado.categorias
    )

    print(
        "[OK] Consulta de concorrência roteada."
    )


def testar_pergunta_sem_dados() -> None:
    """Conversa comum não deve enviar ferramentas."""

    resultado = rotear_ferramentas(
        "Explique em uma frase qual é a sua função."
    )

    assert resultado.intencao == "conversa"
    assert len(resultado.ferramentas) == 0

    print(
        "[OK] Pergunta comum sem ferramentas."
    )


def testar_limite() -> None:
    """Nenhuma rota deve ultrapassar o limite definido."""

    perguntas = [
        (
            "Analise margem, estoque, fornecedor, compra, venda, "
            "campanha, concorrentes e preços."
        ),
        (
            "Cadastre uma venda e consulte produto, estoque, "
            "fornecedor, compra e campanha."
        ),
    ]

    for pergunta in perguntas:
        resultado = rotear_ferramentas(
            pergunta
        )

        assert (
            len(resultado.ferramentas)
            <= LIMITE_FERRAMENTAS_POR_REQUISICAO
        )

    print(
        "[OK] Limite máximo respeitado."
    )


def testar_sem_duplicacao() -> None:
    """A rota não deve conter ferramentas duplicadas."""

    resultado = rotear_ferramentas(
        "Registre uma venda e verifique produto e estoque."
    )

    nomes = resultado.nomes_ferramentas

    assert len(nomes) == len(
        set(nomes)
    )

    print(
        "[OK] Nenhuma ferramenta duplicada."
    )


def testar_reducao_real() -> None:
    """Confirma redução em relação às 70 ferramentas."""

    todas = criar_ferramentas()

    resultado = rotear_ferramentas(
        "Quais são os alertas prioritários da empresa?"
    )

    assert len(todas) == 70

    assert len(
        resultado.ferramentas
    ) < len(todas)

    print(
        "[OK] Roteamento reduziu "
        f"{len(todas)} para "
        f"{len(resultado.ferramentas)} ferramentas."
    )


def mostrar_exemplos() -> None:
    """Exibe exemplos para inspeção visual."""

    perguntas = [
        "Quais são os principais riscos da empresa?",
        "Registre uma venda do produto 1.",
        "Liste todos os fornecedores.",
        "Qual fornecedor é melhor para reposição?",
        "Explique qual é a sua função.",
    ]

    print()
    print("Exemplos de roteamento:")

    for pergunta in perguntas:
        resultado = diagnosticar_roteamento(
            pergunta
        )

        print()
        print(f"Pergunta: {pergunta}")
        print(
            f"Intenção: {resultado['intencao']}"
        )
        print(
            f"Categorias: {resultado['categorias']}"
        )
        print(
            "Quantidade de ferramentas: "
            f"{resultado['quantidade_ferramentas']}"
        )
        print(
            f"Ferramentas: {resultado['ferramentas']}"
        )


def executar_testes() -> None:
    """Executa todos os testes."""

    testar_diagnostico_empresarial()
    testar_registro_venda()
    testar_compra()
    testar_consulta_concorrente()
    testar_pergunta_sem_dados()
    testar_limite()
    testar_sem_duplicacao()
    testar_reducao_real()
    mostrar_exemplos()

    print()
    print(
        "Todos os testes do roteador passaram."
    )


if __name__ == "__main__":
    executar_testes()