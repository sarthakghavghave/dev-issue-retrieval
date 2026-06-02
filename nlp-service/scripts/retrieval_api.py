from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder
import pandas as pd
import faiss
from pathlib import Path

TOP_K = 20
FINAL_K = 10

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

app = FastAPI()

embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

index = faiss.read_index(str(INDEX_PATH))
metadata = pd.read_parquet(METADATA_PATH)
metadata = metadata.fillna("")

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search(request: SearchRequest):

    query_embedding = embedder.encode(
        [request.query],
        normalize_embeddings=True
    )

    scores, indices = index.search(query_embedding, TOP_K)

    pairs = []
    candidates = []

    for idx in indices[0]:
        row = metadata.iloc[idx]

        pairs.append([
            request.query,
            row["retrieval_text"][:2000]
        ])

        candidates.append(row)

    rerank_scores = reranker.predict(pairs)

    ranked = sorted(
        zip(candidates, rerank_scores),
        key=lambda x: x[1],
        reverse=True
    )

    results = []
    for row, score in ranked[:FINAL_K]:
        if score >= 5:
            relevance = "Top Match"
        elif score >= 2:
            relevance = "Strong Match"
        else:
            relevance = "Related Issue"

        results.append({
            "title": row["title"],
            "repository": row["repository_name"],
            "url": row["issue_url"],
            "created_at": row["created_at"],
            "body": row["body"][:200],
            "labels": row["labels"],
            "score": float(score),
            "relevance": relevance
        })

    return results