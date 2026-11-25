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
