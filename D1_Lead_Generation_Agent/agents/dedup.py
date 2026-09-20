import re
from urllib.parse import urlparse
import pandas as pd

from .models import Lead


SUFFIXES = [
    "private limited", "pvt ltd", "pvt limited", "limited", "ltd",
    "incorporated", "inc", "corporation", "corp", "llc"
]


def normalize_name(name: str) -> str:
    value = (name or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    for suffix in SUFFIXES:
        value = re.sub(rf"\b{re.escape(suffix)}\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def domain(url: str) -> str:
    if not url or url == "Unknown":
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def deduplicate(leads: list[Lead]) -> tuple[list[Lead], int]:
    rows = [lead.model_dump() for lead in leads]
    if not rows:
        return [], 0

    df = pd.DataFrame(rows)
    df["_name_key"] = df["company_name"].map(normalize_name)
    df["_domain_key"] = df["website"].map(domain)

    emails = df["email"].fillna("").astype(str).str.lower().str.strip()
    emails = emails.replace({"unknown": "", "nan": ""})
    df["_email_key"] = emails

    # Completeness score: prefer the record with more usable fields.
    usable = ["website", "industry", "location", "employee_count",
              "technology_signal", "funding_signal", "hiring_signal",
              "growth_signal", "contact_name", "job_title", "source_url"]
    df["_complete"] = 0
    for col in usable:
        df["_complete"] += df[col].apply(
            lambda x: 0 if x in ("", "Unknown", None, 0, False) else 1
        )

    # Sort so the most complete record is retained.
    df = df.sort_values("_complete", ascending=False)

    seen = set()
    keep_rows = []
    duplicates = 0

    for _, row in df.iterrows():
        keys = []
        if row["_email_key"]:
            keys.append(("email", row["_email_key"]))
        if row["_domain_key"]:
            keys.append(("domain", row["_domain_key"]))
        if row["_name_key"]:
            keys.append(("name", row["_name_key"]))

        if any(key in seen for key in keys):
            duplicates += 1
            continue

        seen.update(keys)
        keep_rows.append(row)

    out = pd.DataFrame(keep_rows)
    for col in ["_name_key", "_domain_key", "_email_key", "_complete"]:
        if col in out.columns:
            out = out.drop(columns=[col])

    result = [Lead(**row.to_dict()) for _, row in out.iterrows()]
    return result, duplicates
