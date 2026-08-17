from typing import Literal

from pydantic import BaseModel, Field, field_validator

# No genuine natural-language question approaches this. The cap is a
# correctness fix as much as a cost one: text-embedding-3-small rejects inputs
# over 8191 tokens, and embedder.py has no handler for that error — so an
# oversized question currently becomes an unhandled 500 rather than a clear
# rejection. Validating at the boundary turns it into a 422 that says why.
#
# nginx independently caps the request body at 16k (see nginx/templates/), which
# stops the pathological cases before a worker is allocated. This is the precise
# limit; that one is the blunt one.
MAX_QUESTION_LENGTH = 1000


class QueryRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_LENGTH)
    # Explicit window picked in the UI's segmented control — replaces the old
    # approach of sniffing time phrases out of the question text.
    time_window: Literal["today", "week", "month"] = "today"

    @field_validator("question")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question cannot be blank")
        return v.strip()
