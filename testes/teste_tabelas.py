from sqlalchemy import inspect

from database.conexao import engine


inspetor = inspect(engine)
tabelas = sorted(inspetor.get_table_names())

print("Tabelas encontradas:")

for tabela in tabelas:
    print(f"- {tabela}")

tabelas_esperadas = {
    "produto",
    "estoque",
    "fornecedor",
    "compra",
    "venda",
    "concorrente",
    "preco_concorrente",
    "campanha",
    "campanha_produto",
}

faltando = tabelas_esperadas.difference(tabelas)

if faltando:
    raise RuntimeError(
        f"As seguintes tabelas não foram criadas: {sorted(faltando)}"
    )

print("\nTodas as tabelas foram criadas corretamente.")