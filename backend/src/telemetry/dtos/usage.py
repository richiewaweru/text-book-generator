from __future__ import annotations

from pydantic import BaseModel, Field


class LLMUsageBreakdownItem(BaseModel):
    key: str
    calls: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class LLMUsageResponse(BaseModel):
    total_calls: int
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    by_caller: list[LLMUsageBreakdownItem] = Field(default_factory=list)
    by_model: list[LLMUsageBreakdownItem] = Field(default_factory=list)
    by_slot: list[LLMUsageBreakdownItem] = Field(default_factory=list)
