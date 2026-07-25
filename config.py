from pathlib import Path

# Diretório raiz do projeto
ROOT_DIR = Path(__file__).parent

# Banco de dados
DATABASE_URL = f"sqlite:///{ROOT_DIR}/database/empresa.db"

# Pasta de documentos do RAG
PASTA_DOCUMENTOS = ROOT_DIR / "dados" / "pdf"

# Pasta dos CSVs
PASTA_CSV = ROOT_DIR / "dados" / "csv"