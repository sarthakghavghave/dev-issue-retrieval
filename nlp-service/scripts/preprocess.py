import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

from scripts.config import CSV_PATH, build_database_url
from scripts.preprocessing import FILTER_REASON_DUPLICATE, preprocess_issue

FETCH_ALL_QUERY = """
SELECT
    github_issue_id,
    repository_name,
    title,
    body,
    labels,
    issue_url,
    created_at
FROM issues
"""


def export_to_csv(output_path: Path | None = None) -> None:
    """Legacy CSV export: fetch all issues, preprocess, write cleaned_issues.csv."""
    output_path = output_path or CSV_PATH
    engine = create_engine(build_database_url())

    df = pd.read_sql(text(FETCH_ALL_QUERY), engine)
    print(f"\nLoaded rows: {len(df)}")

    processed_rows = []
    seen_keys = set()

    for _, row in tqdm(df.iterrows(), total=len(df)):
        processed, filter_reason = preprocess_issue(row)

        if filter_reason is None:
            title_key = processed["title"].strip().lower()
            repo_key = str(row.get("repository_name", "") or "").strip().lower()
            dup_key = (title_key, repo_key)
            if title_key and repo_key and dup_key in seen_keys:
                filter_reason = FILTER_REASON_DUPLICATE

        if filter_reason is not None:
            continue

        seen_keys.add(dup_key)
        date = row["created_at"]
        if hasattr(date, "strftime"):
            date = date.strftime("%Y-%m-%d")

        processed_rows.append(
            {
                "github_issue_id": row["github_issue_id"],
                "repository_name": row["repository_name"],
                "title": processed["title"],
                "labels": processed["labels"],
                "body": processed["body"],
                "issue_url": row["issue_url"],
                "created_at": date,
                "retrieval_text": processed["retrieval_text"],
            }
        )

    processed_df = pd.DataFrame(processed_rows)
    processed_df = processed_df.fillna("")

    print(f"\nRemaining rows after filtering: {len(processed_df)}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed_df.to_csv(output_path, index=False, encoding="utf-8-sig", quoting=1)
    print("\nPreprocessing completed.\n")


def main():
    parser = argparse.ArgumentParser(description="Preprocess issues from Neon DB to CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=CSV_PATH,
        help="Output CSV path",
    )
    args = parser.parse_args()
    export_to_csv(args.output)


if __name__ == "__main__":
    main()
