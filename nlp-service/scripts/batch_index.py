"""Batch-process PENDING issues from Neon DB: preprocess, filter, embed, update status."""

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/batch_index.py` from nlp-service root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from scripts.config import BATCH_SIZE, MODEL_NAME
from scripts.db import (
    count_by_status,
    fetch_indexed_title_keys,
    fetch_pending_issues,
    mark_indexing,
    update_issues_status_batch,
)
from scripts.incremental_update import update_index
from scripts.preprocessing import FILTER_REASON_DUPLICATE, preprocess_issue


def merge_stats(totals: dict, batch: dict) -> dict:
    return {
        "processed": totals.get("processed", 0) + batch.get("processed", 0),
        "indexed": totals.get("indexed", 0) + batch.get("indexed", 0),
        "filtered": totals.get("filtered", 0) + batch.get("filtered", 0),
        "failed": totals.get("failed", 0) + batch.get("failed", 0),
    }


def process_batch(embedder, batch_size: int, seen_keys: set) -> dict:
    pending = fetch_pending_issues(batch_size)
    if pending.empty:
        return {"processed": 0, "indexed": 0, "filtered": 0, "failed": 0}

    issue_ids = pending["id"].tolist()
    marked = mark_indexing(issue_ids)
    if marked == 0:
        return {"processed": 0, "indexed": 0, "filtered": 0, "failed": 0}

    status_updates = []
    to_index = []
    stats = {"processed": 0, "indexed": 0, "filtered": 0, "failed": 0}

    for _, row in pending.iterrows():
        stats["processed"] += 1
        issue_id = int(row["id"])
        dup_key = ("", "")

        try:
            processed, filter_reason = preprocess_issue(row)
        except Exception:
            status_updates.append((issue_id, "FAILED", "NONE"))
            stats["failed"] += 1
            continue

        if filter_reason is None:
            title_key = processed["title"].strip().lower()
            repo_key = str(row.get("repository_name", "") or "").strip().lower()
            dup_key = (title_key, repo_key)
            if title_key and repo_key and dup_key in seen_keys:
                filter_reason = FILTER_REASON_DUPLICATE

        if filter_reason is not None:
            status_updates.append((issue_id, "FILTERED", filter_reason))
            stats["filtered"] += 1
            continue

        seen_keys.add(dup_key)
        to_index.append(processed)

    if status_updates:
        update_issues_status_batch(status_updates)

    if to_index:
        try:
            result = update_index(to_index, embedder)
            if result.get("status") != "ok":
                for row in to_index:
                    status_updates.append((int(row["id"]), "FAILED", "NONE"))
                update_issues_status_batch(status_updates)
                stats["failed"] += len(to_index)
            else:
                indexed_updates = [
                    (int(row["id"]), "INDEXED", "NONE") for row in to_index
                ]
                update_issues_status_batch(indexed_updates)
                stats["indexed"] += len(to_index)
        except Exception:
            failed_updates = [(int(row["id"]), "FAILED", "NONE") for row in to_index]
            update_issues_status_batch(failed_updates)
            stats["failed"] += len(to_index)

    return stats


def process_pending_issues(
    embedder,
    batch_size: int = BATCH_SIZE,
    max_batches: int | None = None,
) -> dict:
    print(f"\nConnecting to Neon and loading embedder ({MODEL_NAME})...")
    if embedder is None:
        embedder = SentenceTransformer(MODEL_NAME)

    pending_count = count_by_status("PENDING")
    print(f"Pending issues in database: {pending_count}")

    seen_keys = fetch_indexed_title_keys()
    print(f"Existing indexed title keys loaded: {len(seen_keys)}")

    totals = {"processed": 0, "indexed": 0, "filtered": 0, "failed": 0}
    batch_num = 0

    while True:
        if max_batches is not None and batch_num >= max_batches:
            break

        batch_stats = process_batch(embedder, batch_size, seen_keys)
        if batch_stats["processed"] == 0:
            break

        batch_num += 1
        totals = merge_stats(totals, batch_stats)

        print(
            f"Batch {batch_num}: processed={batch_stats['processed']} "
            f"indexed={batch_stats['indexed']} filtered={batch_stats['filtered']} "
            f"failed={batch_stats['failed']}"
        )

    remaining_pending = count_by_status("PENDING")
    print(
        f"\nDone. Total processed={totals['processed']} indexed={totals['indexed']} "
        f"filtered={totals['filtered']} failed={totals['failed']}"
    )
    print(f"Remaining pending: {remaining_pending}\n")

    return {
        **totals,
        "remaining_pending": remaining_pending,
    }


def run(batch_size: int, max_batches: int | None = None) -> None:
    process_pending_issues(None, batch_size=batch_size, max_batches=max_batches)


def main():
    parser = argparse.ArgumentParser(
        description="Process PENDING GitHub issues from Neon DB into FAISS index."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Issues per batch (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Stop after N batches (default: process all pending)",
    )
    args = parser.parse_args()
    run(batch_size=args.batch_size, max_batches=args.max_batches)


if __name__ == "__main__":
    main()
