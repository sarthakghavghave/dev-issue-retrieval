import os
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"
CSV_PATH = BASE_DIR / "data/processed/cleaned_issues.csv"


def build_database_url() -> str:
    """Build a SQLAlchemy URL from env vars.

    Supports either a full DATABASE_URL or Neon-style split vars
    (NEON_URL, NEON_NAME, NEON_PASSWORD) matching the Java backend.
    """
    direct = os.getenv("DATABASE_URL")
    if direct:
        if direct.startswith("postgres://"):
            return direct.replace("postgres://", "postgresql+psycopg2://", 1)
        return direct

    jdbc_url = os.getenv("NEON_URL")
    user = os.getenv("NEON_NAME")
    password = os.getenv("NEON_PASSWORD")

    if not all([jdbc_url, user, password]):
        raise ValueError(
            "Database credentials missing. Set DATABASE_URL or "
            "NEON_URL + NEON_NAME + NEON_PASSWORD."
        )

    if jdbc_url.startswith("jdbc:"):
        jdbc_url = jdbc_url[len("jdbc:"):]

    parsed = urlparse(jdbc_url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/neondb"
    query = f"?{parsed.query}" if parsed.query else ""

    auth = f"{quote_plus(user)}:{quote_plus(password)}"
    return f"postgresql+psycopg2://{auth}@{host}{port}{path}{query}"
