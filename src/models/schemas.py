from pydantic import BaseModel
from typing import Any

class IngestedItem(BaseModel):
    source: str
    title: str
    url: str
    published_at: str | None = None
    text: str | None = None
    metadata: dict[str, Any] = {}
