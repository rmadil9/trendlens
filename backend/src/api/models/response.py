from pydantic import BaseModel


class Source(BaseModel):
    title: str
    url: str
    source: str
    published_at: int  # Unix timestamp — the frontend decides how to format it for display


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
