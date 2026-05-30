import re
import pandas as pd

from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from tqdm import tqdm

DB_URL = "postgresql://postgres:JayData%405432@localhost:5432/dev_issue_retrieval"

engine = create_engine(DB_URL)
query = """
SELECT
    github_issue_id,
    repository_name,
    title,
    body,
    labels,
    issue_url
FROM issues
"""

df = pd.read_sql(query, engine)
print(f"\nLoaded rows: {len(df)}")

NOISE_PATTERNS = [
    "dependabot",
    "forward port",
    "upgrade to ",
    "bump ",
    "release",
    "license header",
    "version bump",
    "changelog"
]

NOISE_LABELS = {
    "team-only",
    "dependency-upgrade",
    "forward-port"
}

LOW_VALUE_PREFIXES = {
    "document ",
    "docs ",
    "documentation ",
    "rename ",
    "cleanup ",
    "changelog "
}

# USEFUL_LABEL_BLACKLIST = {
#     "waiting-for-triage",
#     "triage",
#     "status: waiting-for-triage",
#     "status: declined",
#     "status: duplicate",
#     "status: invalid",
#     "status: superseded"
# }

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
        if (label.startswith("status:")
            or label.startswith("for:")
            or label.startswith("team:")
            or label.startswith("priority:")
        ):
            continue

        # remove low semantic labels
        if label in {
            "task",
            "duplicate",
            "invalid",
            "question",
            "documentation"
        }:
            continue

        useful.append(label)

    return " ".join(useful)

def is_noise(title, labels):
    combined = f"{title} {labels}".lower()
    if any(pattern in combined for pattern in NOISE_PATTERNS):
        return True

    label_set = {
        label.strip().lower()
        for label in labels.split(",")
    }

    if any(label in label_set for label in NOISE_LABELS):
        return True

    if any(combined.startswith(prefix) for prefix in LOW_VALUE_PREFIXES):
        return True

    return False

processed_rows = []

for _, row in tqdm(df.iterrows(), total=len(df)):

    title = clean_text(row["title"])
    body = clean_text(row["body"])
    labels = filter_labels(row["labels"])

    # skip noisy maintenance issues
    if is_noise(title, labels):
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
        "retrieval_text": retrieval_text.strip()
    })

processed_df = pd.DataFrame(processed_rows)
print(f"\nRemaining rows after filtering: {len(processed_df)}")
processed_df.to_csv("cleaned_issues.csv", index=False, encoding="utf-8-sig", quoting=1)
print("\nPreprocessing completed.")