import faiss
import pandas as pd
import numpy as np
import re
import shutil
import tempfile
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"


def clean_text(text):
    if pd.isna(text):
        return ""

    text = str(text)
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"#+", " ", text)
    text = re.sub(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
        " ",
        text
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess_incremental_issue(row):
    row["title"] = clean_text(row.get("title", ""))
    row["body"] = clean_text(row.get("body", ""))
    row["labels"] = clean_text(str(row.get("labels", "") or ""))
    comments = clean_text(row.get("comments", ""))
    row["comments"] = comments[:1500]
    return row


def build_retrieval_text(row):
    title = str(row.get("title", "") or "").strip()
    body = str(row.get("body", "") or "").strip()
    labels = str(row.get("labels", "") or "").strip()
    repository = str(row.get("repository_name", "") or "").strip()
    comments = str(row.get("comments", "") or "").strip()

    comments_section = f"\n\nComments:\n{comments}" if comments else ""

    return f"Repository: {repository}\n\nTitle: {title}\n\nLabels: {labels}\n\nBody:\n{body}{comments_section}".strip()


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
        new_df = pd.read_parquet(BASE_DIR / "data/incremental/new_issues.parquet")
    else:
        new_df = pd.DataFrame(new_issues)

    if new_df.empty:
        return {"status": "no new issues", "added": 0, "total": 0}

    if "github_issue_id" not in new_df.columns:
        raise ValueError("github_issue_id is required for incremental update")

    # Drop rows missing the id - we cannot upsert them safely.
    new_df = new_df.dropna(subset=["github_issue_id"]).copy()
    if new_df.empty:
        return {"status": "no valid new issues", "added": 0, "total": 0}

    # Normalize types up front so the merge logic is consistent.
    new_df["github_issue_id"] = new_df["github_issue_id"].astype("int64")
    new_df = new_df.drop_duplicates(subset=["github_issue_id"], keep="last")

    new_df = new_df.apply(preprocess_incremental_issue, axis=1)

    if "retrieval_text" not in new_df.columns:
        new_df["retrieval_text"] = new_df.apply(build_retrieval_text, axis=1)

    new_df = new_df.fillna("")

    # Drop rows whose retrieval text is empty - they would only add noisy
    # (or zero) vectors to the index.
    new_df = new_df[new_df["retrieval_text"].astype(str).str.strip() != ""]
    if new_df.empty:
        return {"status": "no valid new issues", "added": 0, "total": 0}

    embeddings = embedder.encode(
        new_df["retrieval_text"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Track this locally because the `existing_ids` variable in the `else`
    # branch is not visible in the cold-start branch.
    replaced_count = 0
    total_after = 0

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        # Cold start - there is no existing index to merge with. Build a fresh
        # IDMap so subsequent incremental calls can upsert into it.
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

        # Ensure the in-memory index supports remove_ids / add_with_ids.
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

    # Persist atomically.
    _safe_write_index(index, INDEX_PATH)
    _safe_write_parquet(metadata, METADATA_PATH)

    print(f"Added {len(new_df)} issues | FAISS size: {total_after}")

    return {
        "status": "ok",
        "added": int(len(new_df)),
        "replaced": int(replaced_count),
        "total": total_after,
    }