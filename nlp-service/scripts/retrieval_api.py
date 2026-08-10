from typing import List, Optional
from fastapi import FastAPI, Body
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder
import pandas as pd
import faiss
from pathlib import Path

from scripts.batch_index import process_pending_issues

TOP_K = 10
FINAL_K = 5
RERANK_K = 5

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

app = FastAPI()

embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
reranker = CrossEncoder("cross-encoder/ms-marco-TinyBERT-L-2-v2")

index = None
metadata = None
index_is_id_map = False
id_to_pos = {}

class SearchRequest(BaseModel):
    query: str

class IssueUpdateDto(BaseModel):
    github_issue_id: int
    repository_name: str
    title: str
    body: str
    labels: str = ""
    issue_url: str
    created_at: str
    updated_at: str = ""
    comments: str = ""
    comments_url: str = ""


class ProcessPendingRequest(BaseModel):
    batch_size: int = 50
    max_batches: Optional[int] = None


def load_index_data():
    global index, metadata, index_is_id_map, id_to_pos
    index = faiss.read_index(str(INDEX_PATH))
    index_is_id_map = hasattr(index, "add_with_ids")
    metadata = pd.read_parquet(str(METADATA_PATH))

    if index_is_id_map and "github_issue_id" in metadata.columns:
        metadata = metadata.drop_duplicates(subset=["github_issue_id"], keep="last").reset_index(drop=True)
        id_to_pos = {
            int(row["github_issue_id"]): idx
            for idx, row in metadata.iterrows()
            if pd.notna(row["github_issue_id"])
        }
    else:
        id_to_pos = {}

    metadata = metadata.fillna("")


load_index_data()

@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/stats")
def get_stats():
    return {
        "index_size": int(index.ntotal) if index is not None else 0,
        "metadata_size": int(len(metadata)) if metadata is not None else 0
    }


@app.post("/update-index")
def update_index_endpoint(issues: Optional[List[IssueUpdateDto]] = Body(default=None)):
    from scripts.incremental_update import update_index as incremental_index_update

    try:
        if issues:
            issue_dicts = [issue.dict() for issue in issues]
            result = incremental_index_update(issue_dicts, embedder)
        else:
            result = incremental_index_update(None, embedder)
    except Exception as ex:
        return {"status": "error", "message": str(ex), "added": 0, "replaced": 0, "total": 0}

    try:
        pending_result = process_pending_issues(
            embedder,
            batch_size=max(20, min(100, len(issues or []) or 50)),
            max_batches=1,
        )
        result["pending_processing"] = pending_result
    except Exception as ex:
        result["pending_processing_error"] = str(ex)

    try:
        load_index_data()
    except Exception as ex:
        return {"status": "warning", "message": "index updated but reload failed: " + str(ex), **result}

    return {"status": "ok", **result}


@app.post("/process-pending")
def process_pending_endpoint(request: Optional[ProcessPendingRequest] = Body(default=None)):
    try:
        batch_size = request.batch_size if request else 50
        max_batches = request.max_batches if request else None
        result = process_pending_issues(embedder, batch_size=batch_size, max_batches=max_batches)
        return {"status": "ok", **result}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}


@app.post("/search")
def search(request: SearchRequest):

    print("Query received:", request.query)
    query_embedding = embedder.encode(
        [request.query],
        normalize_embeddings=True
    )

    scores, indices = index.search(query_embedding, TOP_K)

    # This is reranking stage
    pairs = []
    candidates = []

    if index_is_id_map:
        for raw_id in indices[0][:RERANK_K]:
            if raw_id < 0:
                continue
            position = id_to_pos.get(int(raw_id))
            if position is None:
                continue
            row = metadata.iloc[position]
            pairs.append([
                request.query,
                row["retrieval_text"][:1000]
            ])
            candidates.append(row)
    else:
        for idx in indices[0][:RERANK_K]:
            row = metadata.iloc[idx]
            pairs.append([
                request.query,
                row["retrieval_text"][:1000]
            ])
            candidates.append(row)

    if not pairs:
        return []

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