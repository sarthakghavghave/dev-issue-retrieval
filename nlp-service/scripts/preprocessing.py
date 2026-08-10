import re
from typing import Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

# Matches backend FilterReason enum values.
FILTER_REASON_FORWARD_PORT = "FORWARD_PORT"
FILTER_REASON_UPGRADE = "UPGRADE"
FILTER_REASON_EMPTY_CONTENT = "EMPTY_CONTENT"
FILTER_REASON_DOCUMENTATION = "DOCUMENTATION"
FILTER_REASON_DUPLICATE = "DUPLICATE"
FILTER_REASON_OTHER = "OTHER"

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
    "markdown docs",
    "document ",
    "documented ",
    "typo",
    "test ",
    "integration test",
    "null check",
    "line endings",
    "polish code",
]

NOISE_LABEL_PREFIXES = [
    "status:",
    "for:",
    "priority:",
    "team:",
]

NOISE_LABELS = {
    "task",
    "documentation",
    "dependency-upgrade",
    "forward-port",
    "team-only",
    "duplicate",
    "invalid",
    "superseded",
}

DOCUMENTATION_PATTERNS = [
    "documentation",
    "docs:",
    "document ",
    "documented ",
    "markdown docs",
]

UPGRADE_PATTERNS = [
    "upgrade to",
    "bump ",
    "dependabot",
]


def clean_text(text) -> str:
    if pd.isna(text):
        return ""

    text = str(text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        " ",
        text,
    )
    text = re.sub(r"```(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"#+", " ", text)
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def filter_labels(labels) -> str:
    if pd.isna(labels):
        return ""

    useful = []
    for label in str(labels).split(","):
        label = re.sub(r"\s+", " ", label.strip().lower())

        if any(label.startswith(prefix) for prefix in NOISE_LABEL_PREFIXES):
            continue
        if label in NOISE_LABELS:
            continue

        useful.append(label)

    return " ".join(useful)


def detect_filter_reason(
    title: str,
    body: str,
    raw_labels: str = "",
) -> Optional[str]:
    title_lower = title.lower()
    body_lower = body.lower()
    labels_lower = (raw_labels or "").lower()

    if body_lower.startswith("forward port of issue") or "forward port" in title_lower:
        return FILTER_REASON_FORWARD_PORT

    if (
        body_lower.startswith("upgrade to ")
        or any(pattern in title_lower for pattern in UPGRADE_PATTERNS)
    ):
        return FILTER_REASON_UPGRADE

    if any(pattern in title_lower for pattern in DOCUMENTATION_PATTERNS):
        return FILTER_REASON_DOCUMENTATION

    if "duplicate" in labels_lower:
        return FILTER_REASON_DUPLICATE

    if len(title) < 5 and len(body) < 30:
        return FILTER_REASON_EMPTY_CONTENT

    if any(pattern in title_lower for pattern in NOISE_TITLE_PATTERNS):
        return FILTER_REASON_OTHER

    return None


def build_retrieval_text(row) -> str:
    title = str(row.get("title", "") or "").strip()
    body = str(row.get("body", "") or "").strip()
    labels = str(row.get("labels", "") or "").strip()
    repository = str(row.get("repository_name", "") or "").strip()
    comments = str(row.get("comments", "") or "").strip()

    comments_section = f"\n\nComments:\n{comments}" if comments else ""

    return (
        f"Repository: {repository}\n\n"
        f"Title: {title}\n\n"
        f"Labels: {labels}\n\n"
        f"Body:\n{body}{comments_section}"
    ).strip()


def preprocess_issue(row) -> Tuple[dict, Optional[str]]:
    """Clean an issue row and return (processed_row, filter_reason).

    filter_reason is None when the issue should be indexed.
    """
    processed = dict(row)

    processed["title"] = clean_text(row.get("title", ""))
    processed["body"] = clean_text(row.get("body", ""))
    processed["labels"] = filter_labels(row.get("labels", ""))

    comments = clean_text(row.get("comments", ""))
    if comments:
        processed["comments"] = comments[:1500]
    else:
        processed["comments"] = ""

    filter_reason = detect_filter_reason(
        processed["title"],
        processed["body"],
        str(row.get("labels", "") or ""),
    )

    if filter_reason is None:
        retrieval_text = build_retrieval_text(processed)
        if not retrieval_text.strip():
            filter_reason = FILTER_REASON_EMPTY_CONTENT
        else:
            processed["retrieval_text"] = retrieval_text

    return processed, filter_reason
