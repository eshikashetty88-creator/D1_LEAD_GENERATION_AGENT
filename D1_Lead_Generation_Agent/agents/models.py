from typing import List
from pydantic import BaseModel, Field


class ICP(BaseModel):
    industry: str = "B2B SaaS"
    min_employees: int = 50
    max_employees: int = 500
    geography: str = "India"
    signals: str = "Hiring / Growth"
    target_roles: str = "Founder, CEO, CTO, Head of Security"
    lead_count: int = 10


class Lead(BaseModel):
    lead_id: str = ""
    company_name: str = "Unknown"
    website: str = "Unknown"
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
    source_url: str = "Unknown"
    source_urls: List[str] = Field(default_factory=list)
    source_notes: str = ""
    data_confidence: str = "Low"
    duplicate_status: str = "Unique"
    industry_points: int = 0
    size_points: int = 0
    geography_points: int = 0
    signal_points: int = 0
    technology_points: int = 0
    confidence_points: int = 0
    icp_score: int = 0
    qualification: str = "Needs review"
    score_reasoning: str = ""


class PipelineResult(BaseModel):
    leads: List[Lead]
    discovered_count: int
    duplicates_removed: int
    unique_count: int
    qualified_count: int
    average_score: float
    skipped_urls: List[str] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
