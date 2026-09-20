import os
import time
import requests
from dotenv import load_dotenv

from .cache import get_cached, set_cached
from .models import ICP, Lead
from .robots_checker import check_robots

load_dotenv()


def build_queries(icp: ICP) -> list[str]:
    base = f'"{icp.industry}" "{icp.geography}" "{icp.min_employees}-{icp.max_employees}"'
    return [
        f'{icp.industry} companies {icp.geography} hiring',
        f'{icp.industry} startups {icp.geography} {icp.signals}',
        f'{icp.industry} "{icp.geography}" "careers"',
        f'{icp.industry} {icp.geography} "{icp.target_roles.split(",")[0].strip()}"',
    ]


def search_serper(query: str, num: int = 8) -> list[dict]:
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        return []

    cached = get_cached("serper", query, ttl_hours=float(os.getenv("CACHE_TTL_HOURS", "24")))
    if cached is not None:
        return cached

    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num},
                timeout=20,
            )
            if response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            results = response.json().get("organic", [])
            set_cached("serper", query, results)
            return results
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Serper search failed after retries: {last_error}")


def discover(icp: ICP) -> tuple[list[Lead], list[str]]:
    """Search only. It does not fetch result pages."""
    leads: list[Lead] = []
    logs: list[str] = []
    queries = build_queries(icp)
    num = int(os.getenv("SEARCH_RESULTS", "8"))

    if os.getenv("FORCE_MOCK") == "1":
        logs.append("Mock/demo mode enabled by the user.")
        return [], logs

    if not os.getenv("SERPER_API_KEY"):
        logs.append("SERPER_API_KEY not configured; using mock/demo discovery.")
        return [], logs

    seen = set()
    for query in queries:
        try:
            results = search_serper(query, num=num)
            logs.append(f"Discovery query returned {len(results)} results: {query}")
        except Exception as exc:
            logs.append(f"Discovery query failed: {query} -> {exc}")
            continue

        for item in results:
            url = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if not url or url in seen:
                continue
            seen.add(url)

            # Mandatory D1 compliance gate: check robots.txt before any page fetch.
            if not check_robots(url):
                logs.append(f"ROBOTS SKIP: {url}")
                continue

            leads.append(
                Lead(
                    company_name=title or "Unknown",
                    website=url,
                    source_url=url,
                    source_urls=[url],
                    source_notes=snippet,
                    industry=icp.industry,
                    location=icp.geography,
                    data_confidence="Low",
                )
            )

    # Keep the first N candidates for the demo.
    return leads[: max(icp.lead_count * 2, icp.lead_count)], logs
