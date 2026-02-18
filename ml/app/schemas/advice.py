"""Pydantic schemas for daily advice endpoints."""

from pydantic import BaseModel


class AdviceResponse(BaseModel):
    date: str
    advice_text: str
    model_name: str
    generation_ms: int | None = None
    cached: bool = False
