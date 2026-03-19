from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import time
from typing import Any, Mapping

from pydantic import ValidationError

from pipeline.events import (
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    event_bus,
)
from pipeline.providers.registry import ModelRoute, ModelSpec, get_node_text_spec
from pipeline.types.requests import GenerationMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2
    base_delay_seconds: float = 0.5


# Best-effort defaults for Anthropic-style pricing (USD per 1M tokens).
# If you need exact pricing, wire env overrides by adjusting this table.
TOKEN_PRICE_USD_PER_1M: dict[ModelRoute, tuple[float, float]] = {
    # input, output
    ModelRoute.TEXT_FAST: (0.25, 1.25),
    ModelRoute.TEXT_STANDARD: (3.0, 15.0),
    ModelRoute.TEXT_CREATIVE: (3.0, 15.0),
}


def _extract_usage(result: Any) -> tuple[int | None, int | None]:
    """
    Extract token usage from pydantic-ai result in a best-effort way.

    pydantic-ai may expose usage with different attribute names depending on
    provider/version; we try common shapes.
    """

    usage = getattr(result, "usage", None)
    if usage is None:
        return None, None

    def get_field(obj: Any, key: str) -> int | None:
        val = None
        if isinstance(obj, Mapping):
            val = obj.get(key)
        else:
            val = getattr(obj, key, None)
        if isinstance(val, (int, float)):
            return int(val)
        return None

    # Input tokens
    input_tokens = (
        get_field(usage, "input_tokens")
        or get_field(usage, "prompt_tokens")
        or get_field(usage, "input_token_count")
        or get_field(usage, "prompt_token_count")
    )

    # Output tokens
    output_tokens = (
        get_field(usage, "output_tokens")
        or get_field(usage, "completion_tokens")
        or get_field(usage, "output_token_count")
        or get_field(usage, "completion_token_count")
    )

    return input_tokens, output_tokens


def _compute_cost_usd(route: ModelRoute, tokens_in: int | None, tokens_out: int | None) -> float | None:
    if tokens_in is None or tokens_out is None:
        return None
    in_usd, out_usd = TOKEN_PRICE_USD_PER_1M.get(route, (0.0, 0.0))
    return (tokens_in / 1_000_000) * in_usd + (tokens_out / 1_000_000) * out_usd


async def run_llm(
    *,
    generation_id: str,
    node: str,
    route: ModelRoute,
    agent: Any,
    user_prompt: str,
    section_id: str | None = None,
    retry_policy: RetryPolicy | None = None,
    spec: ModelSpec | None = None,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> Any:
    """
    Central choke point for LLM calls: retries + tracing events + cost accounting.
    """

    retry_policy = retry_policy or RetryPolicy()
    spec = spec or get_node_text_spec(node, generation_mode=generation_mode)

    attempt = 0
    while attempt < retry_policy.max_attempts:
        attempt += 1
        started_at = time.perf_counter()

        event_bus.publish(
            generation_id,
            LLMCallStartedEvent(
                generation_id=generation_id,
                node=node,
                route=route.value,
                provider=spec.provider,
                model_name=spec.model_name,
                attempt=attempt,
                section_id=section_id,
            ),
        )

        try:
            result = await agent.run(user_prompt=user_prompt)
            latency_ms = (time.perf_counter() - started_at) * 1000.0

            tokens_in, tokens_out = _extract_usage(result)
            cost_usd = _compute_cost_usd(route, tokens_in, tokens_out)

            event_bus.publish(
                generation_id,
                LLMCallSucceededEvent(
                    generation_id=generation_id,
                    node=node,
                    route=route.value,
                    provider=spec.provider,
                    model_name=spec.model_name,
                    attempt=attempt,
                    section_id=section_id,
                    latency_ms=latency_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                ),
            )
            return result
        except ValidationError as exc:
            # Output schema violations are rarely fixed by retrying.
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            event_bus.publish(
                generation_id,
                LLMCallFailedEvent(
                    generation_id=generation_id,
                    node=node,
                    route=route.value,
                    provider=spec.provider,
                    model_name=spec.model_name,
                    attempt=attempt,
                    section_id=section_id,
                    latency_ms=latency_ms,
                    retryable=False,
                    error=str(exc),
                ),
            )
            raise
        except Exception as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            retryable = attempt < retry_policy.max_attempts

            event_bus.publish(
                generation_id,
                LLMCallFailedEvent(
                    generation_id=generation_id,
                    node=node,
                    route=route.value,
                    provider=spec.provider,
                    model_name=spec.model_name,
                    attempt=attempt,
                    section_id=section_id,
                    latency_ms=latency_ms,
                    retryable=retryable,
                    error=str(exc),
                ),
            )

            if not retryable:
                raise

            await asyncio.sleep(retry_policy.base_delay_seconds * attempt)

    # Defensive: should never get here because loop either returns or raises.
    raise RuntimeError("run_llm exhausted retries unexpectedly")

