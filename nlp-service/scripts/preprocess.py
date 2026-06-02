import re
import pandas as pd

from pathlib import Path
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data/processed/cleaned_issues.csv"

DB_URL = "postgresql://postgres:JayData%405432@localhost:5432/dev_issue_retrieval"

engine = create_engine(DB_URL)
query = """
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

df = pd.read_sql(query, engine)
print(f"\nLoaded rows: {len(df)}")

NOISE_TITLE_PATTERNS = [
    "forward port",
    "upgrade to",
    "bump ",
    "dependabot",
    "license file",
    "license header",
    "changelog",
    "release notes",
    "release announcement",
    "documentation",
    "docs:",
    "correct the name",
    "update license",
    "rename ",
    "renames ",
    "license",
    "licence",
    "copyright",
    "changelog",
    "release notes",
    "markdown docs",
    "document ",
    "documented ",
    "typo",
    "test ",
    "integration test",
    "null check",
    "line endings",
    "license",
    "licence",
    "rename ",
    "polish code",
    "forward port",
    "bump ",
    "upgrade to"
]

NOISE_LABEL_PREFIXES = [
    "status:",
    "for:",
    "priority:",
    "team:"
]


NOISE_LABELS = {
    "task",
    "documentation",
    "dependency-upgrade",
    "forward-port",
    "team-only",
    "duplicate",
    "invalid",
    "superseded"
}

def clean_text(text):
    if pd.isna(text):
        return ""

    text = str(text)
    # remove markdown links
    text = re.sub(r'\\[(.*?)\\]\\((.*?)\\)', r'\\1', text)
    # remove html
    text = BeautifulSoup(text, "html.parser").get_text()
    # remove common emoji ranges
    text = re.sub(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        " ",
        text
    )
    # remove code blocks
    text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
    # remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    # remove markdown headings
    text = re.sub(r'#+', ' ', text)
    # remove urls
    text = re.sub(r'http\\S+', ' ', text)
    # normalize spaces
    text = re.sub(r'\\s+', ' ', text)

    return text.strip()

def filter_labels(labels):
    if pd.isna(labels):
        return ""

    useful = []
    for label in labels.split(","):
        label = re.sub(r'\\s+', ' ', label.strip().lower())

        # remove workflow labels
        if any(
                label.startswith(prefix)
                for prefix in NOISE_LABEL_PREFIXES
        ):
            continue

        # remove low semantic labels
        if label in NOISE_LABELS:
            continue

        useful.append(label)

    return " ".join(useful)

def is_noise(title, labels, body):
    title_lower = title.lower()
    if any(pattern in title_lower for pattern in NOISE_TITLE_PATTERNS):
        return True

    body_lower = body.lower()
    if body_lower.startswith("forward port of issue"):
        return True
    if body_lower.startswith("upgrade to "):
        return True

    return False

processed_rows = []
for _, row in tqdm(df.iterrows(), total=len(df)):

    title = clean_text(row["title"])
    body = clean_text(row["body"])
    labels = filter_labels(row["labels"])
    date = row["created_at"].strftime('%Y-%m-%d')

    # skip noisy maintenance issues
    if is_noise(title, labels, body):
        continue

    # skip useless entries
    if len(title) < 5 and len(body) < 30:
        continue

    retrieval_text = f"""
Repository: {row['repository_name']}

Title: {title}

Labels: {labels}

Body:
{body}
"""

    processed_rows.append({
        "github_issue_id": row["github_issue_id"],
        "repository_name": row["repository_name"],
        "title": title,
        "labels": labels,
        "body": body,
        "issue_url": row["issue_url"],
        "created_at": date,
        "retrieval_text": retrieval_text.strip()
    })

processed_df = pd.DataFrame(processed_rows)
processed_df = processed_df.drop_duplicates(subset=["title", "repository_name"])
processed_df = processed_df.fillna("")

print(f"\nRemaining rows after filtering: {len(processed_df)}")
processed_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig", quoting=1)
print("\nPreprocessing completed.\n")