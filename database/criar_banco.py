from database.conexao import Base, engine

# Este import registra todos os modelos no metadata do SQLAlchemy.
import database.models  # noqa: F401


def criar_banco() -> None:
    """Cria todas as tabelas que ainda não existem."""

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    criar_banco()
    print("Banco de dados e tabelas criados com sucesso.")