import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google import genai

from .cache import get_cached, set_cached
from .models import Lead, ICP
from .robots_checker import check_robots

load_dotenv()


class EnrichmentResult(BaseModel):
    company_name: str = "Unknown"
    industry: str = "Unknown"
    location: str = "Unknown"
    employee_count: int = 0
    hiring_signal: bool = False
    growth_signal: bool = False
    technology_signal: str = "Unknown"
    funding_signal: str = "Unknown"
    contact_name: str = "Unknown"
    job_title: str = "Unknown"
    email: str = "Unknown"
    linkedin_url: str = "Unknown"
    data_confidence: str = "Low"
    evidence: list[str] = Field(default_factory=list)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    return text[:20000]


def fetch_allowed(url: str) -> tuple[str, str]:
    """Check robots.txt BEFORE making the page request."""
    if not check_robots(url):
        return "", f"ROBOTS BLOCKED: {url}"

    cached = get_cached("page", url, ttl_hours=float(os.getenv("CACHE_TTL_HOURS", "24")))
    if cached is not None:
        return cached.get("text", ""), f"CACHE HIT: {url}"

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "D1LeadGenerationAgent/1.0"},
            timeout=15,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Re-check the final redirected URL before using the body.
        final_url = response.url
        if final_url != url and not check_robots(final_url):
            return "", f"ROBOTS BLOCKED REDIRECT: {final_url}"

        text = _extract_text(response.text)
        set_cached("page", url, {"text": text, "final_url": final_url})
        time.sleep(float(os.getenv("FETCH_DELAY", "0.8")))
        return text, f"FETCHED: {final_url}"
    except Exception as exc:
        return "", f"FETCH FAILED: {url} -> {exc}"


def enrich_one(lead: Lead, icp: ICP, skipped: list[str], logs: list[str]) -> Lead:
    text, status = fetch_allowed(lead.website)
    logs.append(status)

    if not text:
        if "ROBOTS BLOCKED" in status:
            skipped.append(lead.website)
        return lead

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logs.append("GEMINI_API_KEY missing; keeping discovered fields without AI enrichment.")
        return lead

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    prompt = f"""
You are the Enrichment Agent in a sales lead pipeline.

ICP:
Industry: {icp.industry}
Employee range: {icp.min_employees}-{icp.max_employees}
Geography: {icp.geography}
Signals: {icp.signals}
Target roles: {icp.target_roles}

Extract only information supported by the public page text below.
Never invent a value. Use "Unknown" for unavailable text.
Do not return private personal information.
Public business contact/job information is allowed only when explicitly present on the page.

SOURCE URL:
{lead.website}

PAGE TEXT:
{text}

Return structured data with:
company_name, industry, location, employee_count, hiring_signal,
growth_signal, technology_signal, funding_signal, contact_name,
job_title, email, linkedin_url, data_confidence, evidence.
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": EnrichmentResult,
            },
        )
        result = EnrichmentResult.model_validate_json(response.text)

        lead.company_name = result.company_name or lead.company_name
        lead.industry = result.industry
        lead.location = result.location
        lead.employee_count = result.employee_count
        lead.hiring_signal = result.hiring_signal
        lead.growth_signal = result.growth_signal
        lead.technology_signal = result.technology_signal
        lead.funding_signal = result.funding_signal
        lead.contact_name = result.contact_name
        lead.job_title = result.job_title
        lead.email = result.email
        lead.linkedin_url = result.linkedin_url
        lead.data_confidence = result.data_confidence
        lead.source_urls = list(dict.fromkeys(lead.source_urls + [lead.website]))
        lead.source_notes = " | ".join(result.evidence)
    except Exception as exc:
        logs.append(f"Gemini enrichment failed for {lead.website}: {exc}")

    return lead


def enrich(leads: list[Lead], icp: ICP) -> tuple[list[Lead], list[str], list[str]]:
    skipped: list[str] = []
    logs: list[str] = []
    max_pages = int(os.getenv("MAX_PAGES", "12"))

    enriched = []
    for lead in leads[:max_pages]:
        enriched.append(enrich_one(lead, icp, skipped, logs))

    # Preserve candidates beyond MAX_PAGES without fetching them.
    enriched.extend(leads[max_pages:])
    return enriched, skipped, logs
