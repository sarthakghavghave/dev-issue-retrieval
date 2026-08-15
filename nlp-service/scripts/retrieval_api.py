from typing import List, Optional
from fastapi import FastAPI, Body
from pydantic import BaseModel
import os
from sentence_transformers import SentenceTransformer
import pandas as pd
import faiss
from pathlib import Path
import threading

from scripts.batch_index import process_pending_issues
from scripts.config import MODEL_NAME

TOP_K = int(os.getenv("FAISS_TOP_K", "10"))
FINAL_K = int(os.getenv("FINAL_K", "5"))
RERANK_K = int(os.getenv("RERANK_K", "5"))

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

app = FastAPI()

embedder = SentenceTransformer(MODEL_NAME)

# cross-encoder reranker (can be disabled in low-memory deployments)
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-TinyBERT-L-2-v2")
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() in ("1", "true", "yes")
_reranker = None
_reranker_lock = threading.Lock()

def get_reranker():
    """Lazily instantiate and return the CrossEncoder reranker (thread-safe).

    Returns None if reranking is disabled via `USE_RERANKER`.
    """
    global _reranker
    if not USE_RERANKER:
        return None
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                from sentence_transformers import CrossEncoder
                _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker

index = None
metadata = None
index_is_id_map = False
id_to_pos = {}

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    final_k: Optional[int] = None
    rerank_k: Optional[int] = None
    use_reranker: Optional[bool] = None

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


def resolve_search_params(request: SearchRequest):
    top_k = TOP_K if request.top_k is None else request.top_k
    final_k = FINAL_K if request.final_k is None else request.final_k
    rerank_k = RERANK_K if request.rerank_k is None else request.rerank_k
    use_reranker = USE_RERANKER if request.use_reranker is None else request.use_reranker

    top_k = max(1, min(int(top_k), 100))
    final_k = max(1, min(int(final_k), top_k))
    rerank_k = max(1, min(int(rerank_k), top_k))
    return top_k, final_k, rerank_k, bool(use_reranker)


def relevance_label(score: float, *, reranked: bool) -> str:
    if reranked:
        if score >= 5:
            return "Top Match"
        if score >= 2:
            return "Strong Match"
        return "Related Issue"
    if score >= 0.7:
        return "Top Match"
    if score >= 0.5:
        return "Strong Match"
    return "Related Issue"


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/stats")
def get_stats():
    return {
        "index_size": int(index.ntotal) if index is not None else 0,
        "metadata_size": int(len(metadata)) if metadata is not None else 0
    }


@app.get("/search/config")
def search_config():
    return {
        "top_k": TOP_K,
        "final_k": FINAL_K,
        "rerank_k": RERANK_K,
        "use_reranker": USE_RERANKER,
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
    top_k, final_k, rerank_k, use_reranker = resolve_search_params(request)

    query_embedding = embedder.encode(
        [request.query],
        normalize_embeddings=True
    )

    scores, indices = index.search(query_embedding, top_k)

    pairs = []
    candidates = []
    candidate_scores = []

    if index_is_id_map:
        for i, raw_id in enumerate(indices[0][:rerank_k]):
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
            candidate_scores.append(float(scores[0][i]))
    else:
        for i, idx in enumerate(indices[0][:rerank_k]):
            row = metadata.iloc[idx]
            pairs.append([
                request.query,
                row["retrieval_text"][:1000]
            ])
            candidates.append(row)
            candidate_scores.append(float(scores[0][i]))

    if not pairs:
        return []

    reranked = False
    if use_reranker:
        r = get_reranker()
        if r is not None:
            rerank_scores = r.predict(pairs)
            reranked = True
        else:
            rerank_scores = candidate_scores
    else:
        rerank_scores = candidate_scores

    ranked = sorted(
        zip(candidates, rerank_scores),
        key=lambda x: x[1],
        reverse=True
    )

    results = []
    for row, score in ranked[:final_k]:
        results.append({
            "title": row["title"],
            "repository": row["repository_name"],
            "url": row["issue_url"],
            "created_at": row["created_at"],
            "body": row["body"][:200],
            "labels": row["labels"],
            "score": float(score),
            "relevance": relevance_label(float(score), reranked=reranked),
        })

    return results