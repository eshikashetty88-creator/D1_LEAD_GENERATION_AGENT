from pathlib import Path
import pandas as pd

from .models import Lead


EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


EXPORT_COLUMNS = [
    "lead_id", "company_name", "website", "industry", "location",
    "employee_count", "contact_name", "job_title", "email",
    "linkedin_url", "technology_signal", "funding_signal",
    "hiring_signal", "source_url", "icp_score", "score_reasoning",
    "data_confidence", "duplicate_status"
]


def to_dataframe(leads: list[Lead]) -> pd.DataFrame:
    rows = [lead.model_dump() for lead in leads]
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=EXPORT_COLUMNS)
    return df.rename(columns={
        "technology_signal": "technology_signal",
    })[EXPORT_COLUMNS]


def write_csv(leads: list[Lead], filename: str = "d1_leads.csv") -> Path:
    path = EXPORT_DIR / filename
    to_dataframe(leads).to_csv(path, index=False)
    return path


def write_hubspot_csv(leads: list[Lead], filename: str = "d1_hubspot_import.csv") -> Path:
    df = to_dataframe(leads).copy()
    hubspot = pd.DataFrame({
        "Company name": df["company_name"],
        "Website URL": df["website"],
        "Industry": df["industry"],
        "Country/Region": df["location"],
        "Number of employees": df["employee_count"],
        "Lead score": df["icp_score"],
        "ICP reasoning": df["score_reasoning"],
        "Source URL": df["source_url"],
        "First name": df["contact_name"].where(df["contact_name"] != "Unknown", ""),
        "Job title": df["job_title"],
        "Email": df["email"].where(df["email"] != "Unknown", ""),
        "LinkedIn URL": df["linkedin_url"].where(df["linkedin_url"] != "Unknown", ""),
    })
    path = EXPORT_DIR / filename
    hubspot.to_csv(path, index=False)
    return path
