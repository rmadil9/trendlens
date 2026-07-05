from typing import Literal

from pydantic import BaseModel, field_validator


class QueryRequest(BaseModel):
    question: str
    # Explicit window picked in the UI's segmented control — replaces the old
    # approach of sniffing time phrases out of the question text.
    time_window: Literal["today", "week", "month"] = "today"

    @field_validator("question")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question cannot be blank")
        return v.strip()
