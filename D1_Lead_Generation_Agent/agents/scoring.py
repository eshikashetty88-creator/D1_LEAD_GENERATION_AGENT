from dotenv import load_dotenv
import os

from google import genai
from pydantic import BaseModel

from .models import Lead, ICP

load_dotenv()


class ScoreResult(BaseModel):
    industry_points: int
    size_points: int
    geography_points: int
    signal_points: int
    technology_points: int
    confidence_points: int
    icp_score: int
    qualification: str
    score_reasoning: str


def score_deterministically(lead: Lead, icp: ICP) -> Lead:
    # Transparent fallback and consistency guard.
    industry = 30 if lead.industry.lower().strip() == icp.industry.lower().strip() else 0

    size = 20 if icp.min_employees <= lead.employee_count <= icp.max_employees else 0

    geography = 15 if icp.geography.lower() in lead.location.lower() else 0

    signal = 15 if (lead.hiring_signal or lead.growth_signal) else 0

    tech = 10 if lead.technology_signal not in ("", "Unknown") else 0

    confidence_map = {"high": 10, "medium": 7, "low": 3}
    confidence = confidence_map.get(lead.data_confidence.lower(), 3)

    total = industry + size + geography + signal + tech + confidence

    if total >= 80:
        qualification = "Strong ICP match"
    elif total >= 60:
        qualification = "Potential match"
    else:
        qualification = "Needs review"

    reasons = [
        f"Industry match: +{industry}/30.",
        f"Company size match: +{size}/20.",
        f"Geography match: +{geography}/15.",
        f"Hiring/growth signal: +{signal}/15.",
        f"Technology/use-case evidence: +{tech}/10.",
        f"Data confidence: +{confidence}/10.",
    ]

    lead.industry_points = industry
    lead.size_points = size
    lead.geography_points = geography
    lead.signal_points = signal
    lead.technology_points = tech
    lead.confidence_points = confidence
    lead.icp_score = total
    lead.qualification = qualification
    lead.score_reasoning = " ".join(reasons)
    return lead


def score_with_gemini(lead: Lead, icp: ICP) -> Lead:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return score_deterministically(lead, icp)

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    prompt = f"""
You are the Qualification/Scoring Agent.

Score this lead against the ICP using exactly this rubric:
Industry match: 30
Company size match: 20
Geography match: 15
Hiring/growth signal: 15
Technology/use-case match: 10
Data confidence: 10

ICP:
{icp.model_dump_json()}

LEAD:
{lead.model_dump_json()}

Rules:
- Never award points for evidence marked Unknown.
- Never exceed the category maximum.
- icp_score must equal the sum of all category points.
- Give concise, explicit reasoning.
- Qualification must be one of: Strong ICP match, Potential match, Needs review.
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ScoreResult,
            },
        )
        result = ScoreResult.model_validate_json(response.text)

        # Hard safety check: the application remains the source of truth.
        values = [
            min(max(result.industry_points, 0), 30),
            min(max(result.size_points, 0), 20),
            min(max(result.geography_points, 0), 15),
            min(max(result.signal_points, 0), 15),
            min(max(result.technology_points, 0), 10),
            min(max(result.confidence_points, 0), 10),
        ]
        total = sum(values)

        lead.industry_points, lead.size_points, lead.geography_points, \
            lead.signal_points, lead.technology_points, lead.confidence_points = values
        lead.icp_score = total
        lead.qualification = result.qualification
        lead.score_reasoning = result.score_reasoning
        print(f"Gemini scoring successful for {lead.company_name}")
        return lead
    except Exception as exc:
      print(f"Gemini scoring failed: {exc}")
      return score_deterministically(lead,icp)


def score(leads: list[Lead], icp: ICP) -> list[Lead]:
    return [score_with_gemini(lead, icp) for lead in leads]
