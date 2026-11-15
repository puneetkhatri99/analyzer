from typing import Literal

from pydantic import BaseModel, HttpUrl


# What the model returns for one page, and the job an admin edits and saves. No docstring: it would be sent to
# OpenAI as the schema's description and change the prompt.
class JobExtraction(BaseModel):
    page_type: Literal["job_posting", "not_job_posting", "unreadable"]
    reason: str  # one sentence: what the page is, or why it can't be read
    category: Literal["church", "nonprofit", "other"] | None
    job_title: str | None
    org_name: str | None
    org_website: str | None
    city: str | None
    state: str | None
    country: str | None
    date_posted: str | None
    salary_min: float | None
    salary_max: float | None
    salary_period: Literal["year", "hour"] | None
    hours: Literal["Full-Time", "Part-Time", "Contract", "Intern", "Temp", "Volunteer"] | None
    remote: bool | None
    denomination: str | None
    church_size: int | None


class ChurchFacts(BaseModel):
    church_size: int | None  # average weekly attendance, only if a source states it
    denomination: str | None
    source_url: str | None  # page the attendance figure comes from
    evidence: str | None  # short quote from that page


class ExtractRequest(BaseModel):
    url: HttpUrl


class SaveRequest(BaseModel):
    url: HttpUrl
    dataset: Literal["churches", "nonprofits"]
    method: Literal["page", "web_search"]
    job: JobExtraction
    church_size_source: HttpUrl | None = None  # set when church size came from a web lookup, not the posting
