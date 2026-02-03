from __future__ import annotations

from pydantic import BaseModel, Field
from src.db.models import Item
from src.services.ollama_client import OllamaClient


class GenaiNewsEval(BaseModel):
    relevance_score: int = Field(ge=0, le=100)
    topic: str
    why_it_matters: str
    target_audience: str
    decision: str  # "keep" or "drop"


class ProductIdeasEval(BaseModel):
    idea_type: str
    problem_statement: str
    solution_summary: str
    maturity_level: str
    reusability_score: int = Field(ge=0, le=100)
    decision: str  # "keep" or "drop"


GENAI_SYSTEM = """You are an evaluator for a daily GenAI/AI engineering news digest.
Return ONLY valid JSON matching this schema:
{
  "relevance_score": 0-100,
  "topic": "short label",
  "why_it_matters": "1-2 sentences",
  "target_audience": "who cares",
  "decision": "keep" or "drop"
}
Be strict: keep only high-signal items, drop vague/low-value items.
"""

PRODUCT_SYSTEM = """You are an evaluator for product/startup ideas.
Return ONLY valid JSON matching this schema:
{
  "idea_type": "e.g. B2B SaaS, devtool, consumer",
  "problem_statement": "clear pain",
  "solution_summary": "clear solution",
  "maturity_level": "idea|prototype|market",
  "reusability_score": 0-100,
  "decision": "keep" or "drop"
}
Be strict: keep only strong, actionable ideas.
"""


def _item_to_prompt(item: Item) -> str:
    return f"""Evaluate this item:

TITLE: {item.title}
URL: {item.url}
SOURCE: {item.source}
TEXT: {(item.text or "")[:1200]}
METADATA: {item.metadata_json}
"""


class Evaluator:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    def eval_genai_news(self, item: Item) -> GenaiNewsEval:
        raw = self.ollama.chat_json(GENAI_SYSTEM, _item_to_prompt(item))
        return GenaiNewsEval.model_validate(raw)

    def eval_product_ideas(self, item: Item) -> ProductIdeasEval:
        raw = self.ollama.chat_json(PRODUCT_SYSTEM, _item_to_prompt(item))
        return ProductIdeasEval.model_validate(raw)
