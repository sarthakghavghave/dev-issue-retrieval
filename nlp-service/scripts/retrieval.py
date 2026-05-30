import faiss
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer

TOP_K = 5
MODEL_NAME = "BAAI/bge-small-en-v1.5"

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

model = SentenceTransformer(MODEL_NAME)

INDEX = faiss.read_index(str(INDEX_PATH))
METADATA = pd.read_parquet(str(METADATA_PATH))
METADATA = METADATA.fillna("")

while True:
    query = input("\nQuery: ")
    if query.lower() == "exit":
        break

    query_embedding = model.encode([query], normalize_embeddings=True)
    scores, indices = INDEX.search(query_embedding, TOP_K)
    print("\nTop Results:\n")

    for rank, idx in enumerate(indices[0], start=1):
        row = METADATA.iloc[idx]
        print("=" * 80)
        print(f"Rank: {rank}")
        print(f"Score: {scores[0][rank-1]:.4f}")
        print(f"Title: {row['title']}")
        print(f"Body: {row["body"]}")
        print(f"Repository: {row['repository_name']}")
        print(row["issue_url"])
        print(row["labels"])
        print()