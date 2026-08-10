import faiss
import pandas as pd
import numpy as np
import shutil
import tempfile
from pathlib import Path

from scripts.config import INDEX_PATH, METADATA_PATH
from scripts.preprocessing import build_retrieval_text, preprocess_issue


def _safe_write_index(index, path: Path):
    """Write the FAISS index atomically to avoid leaving a half-written file
    on disk if the process is killed mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        faiss.write_index(index, str(tmp_path))
        shutil.move(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _safe_write_parquet(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        df.to_parquet(str(tmp_path), index=False)
        shutil.move(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def update_index(new_issues=None, embedder=None):

    if embedder is None:
        raise ValueError("embedder is required for incremental update")

    if new_issues is None:
        from scripts.config import BASE_DIR
        new_df = pd.read_parquet(BASE_DIR / "data/incremental/new_issues.parquet")
    else:
        new_df = pd.DataFrame(new_issues)

    if new_df.empty:
        return {"status": "no new issues", "added": 0, "total": 0}

    if "github_issue_id" not in new_df.columns:
        raise ValueError("github_issue_id is required for incremental update")

    new_df = new_df.dropna(subset=["github_issue_id"]).copy()
    if new_df.empty:
        return {"status": "no valid new issues", "added": 0, "total": 0}

    new_df["github_issue_id"] = new_df["github_issue_id"].astype("int64")
    new_df = new_df.drop_duplicates(subset=["github_issue_id"], keep="last")

    processed_rows = []
    for _, row in new_df.iterrows():
        processed, filter_reason = preprocess_issue(row)
        if filter_reason is None:
            processed_rows.append(processed)

    new_df = pd.DataFrame(processed_rows)
    if new_df.empty:
        return {"status": "no valid new issues", "added": 0, "total": 0}

    if "retrieval_text" not in new_df.columns:
        new_df["retrieval_text"] = new_df.apply(build_retrieval_text, axis=1)

    new_df = new_df.fillna("")
    new_df = new_df[new_df["retrieval_text"].astype(str).str.strip() != ""]
    if new_df.empty:
        return {"status": "no valid new issues", "added": 0, "total": 0}

    embeddings = embedder.encode(
        new_df["retrieval_text"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    replaced_count = 0
    total_after = 0

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        dim = len(embeddings[0])
        base_index = faiss.IndexFlatIP(dim)
        index = faiss.IndexIDMap2(base_index)
        metadata = new_df.copy()
        ids_to_add = new_df["github_issue_id"].to_numpy()
        index.add_with_ids(np.array(embeddings).astype("float32"), ids_to_add)
    else:
        index = faiss.read_index(str(INDEX_PATH))
        metadata = pd.read_parquet(str(METADATA_PATH))
        metadata = metadata.fillna("")

        if not isinstance(index, faiss.IndexIDMap):
            if "github_issue_id" in metadata.columns and len(metadata) == index.ntotal:
                dim = index.d
                base_index = faiss.IndexFlatIP(dim)
                mapped_index = faiss.IndexIDMap2(base_index)
                existing_ids_arr = metadata["github_issue_id"].dropna().astype("int64").to_numpy()
                vectors = np.vstack(
                    [index.reconstruct(i) for i in range(index.ntotal)]
                ).astype("float32")
                mapped_index.add_with_ids(vectors, existing_ids_arr)
                index = mapped_index
            else:
                index = faiss.IndexIDMap2(index)

        if "github_issue_id" in metadata.columns:
            existing_ids = set(
                int(x) for x in metadata["github_issue_id"].dropna().astype("int64").tolist()
            )
        else:
            existing_ids = set()

        new_id_set = set(int(x) for x in new_df["github_issue_id"].tolist())
        replaced_ids = existing_ids & new_id_set
        replaced_count = len(replaced_ids)
        if replaced_ids:
            index.remove_ids(np.array(list(replaced_ids), dtype="int64"))
            metadata = metadata[~metadata["github_issue_id"].isin(replaced_ids)]

        ids_to_add = new_df["github_issue_id"].to_numpy()
        index.add_with_ids(np.array(embeddings).astype("float32"), ids_to_add)

        metadata = pd.concat([metadata, new_df], ignore_index=True)
        metadata = metadata.drop_duplicates(subset=["github_issue_id"], keep="last")

    total_after = int(index.ntotal)

    _safe_write_index(index, INDEX_PATH)
    _safe_write_parquet(metadata, METADATA_PATH)

    print(f"Added {len(new_df)} issues | FAISS size: {total_after}")

    return {
        "status": "ok",
        "added": int(len(new_df)),
        "replaced": int(replaced_count),
        "total": total_after,
    }
