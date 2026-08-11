import faiss
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder

from scripts.config import MODEL_NAME

FAISS_TOP_K = 20
FINAL_TOP_K = 10
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

embed_model = SentenceTransformer(MODEL_NAME)
reranker = CrossEncoder(RERANK_MODEL)

INDEX = faiss.read_index(str(INDEX_PATH))
METADATA = pd.read_parquet(str(METADATA_PATH))
METADATA = METADATA.fillna("")

while True:
    query = input("\nQuery: ")

    if query.lower() == "exit":
        break

    query_embedding = embed_model.encode([query], normalize_embeddings=True)
    faiss_scores, faiss_indices = INDEX.search(query_embedding, FAISS_TOP_K)

    candidates = []
    pairs = []

    for idx in faiss_indices[0]:
        row = METADATA.iloc[idx]

        text = row["retrieval_text"]

        candidates.append((idx, row))
        pairs.append([query, text])

    rerank_scores = reranker.predict(pairs)

    results = []

    for score, (idx, row) in zip(rerank_scores, candidates):
        results.append((score, row))

    results.sort(key=lambda x: x[0], reverse=True)

    print("\nTop Results:\n")

    for rank, (score, row) in enumerate(results[:FINAL_TOP_K], start=1):
        print("=" * 80)
        print(f"Rank: {rank}")
        print(f"Rerank Score: {score:.4f}")
        print(f"Title: {row['title']}")
        print(f"Body: {row['body'][:300]}")
        print(f"Repository: {row['repository_name']}")
        print(row["issue_url"])
        print(row["labels"])
        print()