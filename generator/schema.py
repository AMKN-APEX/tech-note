"""Card data schema shared by the generator and the web app."""

from datetime import date as Date

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Connection(BaseModel):
    target: str  # past topic id or term name
    note: str


class TermCard(BaseModel):
    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    field: str


class FlowStep(BaseModel):
    label: str = Field(min_length=1)  # short, ~20 chars
    detail: str  # ~40 chars


class Topic(BaseModel):
    id: str
    title: str
    field: str
    question: str
    summary: list[str] = Field(min_length=3, max_length=3)
    mechanism: str
    terms: list[str]
    connections: list[Connection]
    hook: str
    source_url: HttpUrl
    source_title: str
    flow: list[FlowStep] = Field(default_factory=list, max_length=6)  # 仕組みの流れ図 (3-5 steps)
    video_query: str | None = None  # YouTube search keywords
    image_url: HttpUrl | None = None  # og:image of the source, filled by commit-day


class DayFile(BaseModel):
    date: Date
    new_terms: list[TermCard]
    topics: list[Topic] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _topic_ids_match_date(self):
        prefix = f"{self.date.isoformat()}-"
        for t in self.topics:
            if not t.id.startswith(prefix):
                raise ValueError(f"topic id {t.id!r} must start with {prefix!r}")
        return self


class TermEntry(BaseModel):
    name: str
    definition: str
    field: str
    first_seen: Date
    related_topics: list[str] = []
