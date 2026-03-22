from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import time
from typing import Any, Mapping

from pydantic import ValidationError
from pydantic_ai.exceptions import ModelHTTPError, UserError

from pipeline.events import (
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    event_bus,
)
from pipeline.providers.registry import (
    ModelFamily,
    ModelSlot,
    ModelSpec,
    effective_text_spec,
    endpoint_host,
    get_node_text_slot,
    get_node_text_spec,
)
from pipeline.types.requests import GenerationMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration for the shared LLM execution path."""

    max_attempts: int = 2
    base_delay_seconds: float = 0.5


# Cost keys stay exact by design so we do not guess vendor pricing. Unknown
# models report `cost_usd=None`, which is safer than inventing a fallback rate.
TOKEN_PRICE_USD_PER_1M_BY_MODEL: dict[str, tuple[float, float]] = {
    "anthropic:claude-haiku-4-5-20251001": (0.25, 1.25),
    "anthropic:claude-sonnet-4-6": (3.0, 15.0),
    "test:TestModel": (0.0, 0.0),
}


def _price_key(effective_spec: ModelSpec) -> str:
    """Build the exact pricing key for the resolved runtime model."""

    if effective_spec.family == ModelFamily.OPENAI_COMPATIBLE:
        host = endpoint_host(effective_spec.base_url)
        if host:
            return f"{effective_spec.family.value}:{host}:{effective_spec.model_name}"
    return f"{effective_spec.family.value}:{effective_spec.model_name}"


def _price_per_1m(effective_spec: ModelSpec) -> tuple[float, float] | None:
    """Return the exact configured price row for a resolved model, if known."""

    return TOKEN_PRICE_USD_PER_1M_BY_MODEL.get(_price_key(effective_spec))


def _should_publish_events(generation_id: str) -> bool:
    return bool(generation_id and generation_id.strip())


def _publish_llm_event(generation_id: str, event: Any) -> None:
    if _should_publish_events(generation_id):
        event_bus.publish(generation_id, event)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (UserError, ValidationError)):
        return False
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in {408, 429, 500, 502, 503, 504}
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    try:
        import httpx

        return isinstance(
            exc,
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
            ),
        )
    except ImportError:
        return False


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

    input_tokens = (
        get_field(usage, "input_tokens")
        or get_field(usage, "prompt_tokens")
        or get_field(usage, "input_token_count")
        or get_field(usage, "prompt_token_count")
    )
    output_tokens = (
        get_field(usage, "output_tokens")
        or get_field(usage, "completion_tokens")
        or get_field(usage, "output_token_count")
        or get_field(usage, "completion_token_count")
    )

    return input_tokens, output_tokens


def _compute_cost_usd(
    effective_spec: ModelSpec,
    tokens_in: int | None,
    tokens_out: int | None,
) -> float | None:
    """Compute best-effort cost using exact model pricing only."""

    if tokens_in is None or tokens_out is None:
        return None

    prices = _price_per_1m(effective_spec)
    if prices is None:
        return None

    in_usd, out_usd = prices
    return (tokens_in / 1_000_000) * in_usd + (tokens_out / 1_000_000) * out_usd


async def run_llm(
    *,
    generation_id: str,
    node: str,
    agent: Any,
    user_prompt: str,
    model: Any | None = None,
    slot: ModelSlot | None = None,
    section_id: str | None = None,
    retry_policy: RetryPolicy | None = None,
    spec: ModelSpec | None = None,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> Any:
    """
    Central choke point for LLM calls: retries + tracing events + cost accounting.

    `slot` and the catalog `spec` are derived from the node name so callers do
    not need to duplicate provider-routing logic.

    Callers still pass the concrete `model` object that was given to
    `Agent(model=...)` so diagnostics and cost reflect the real runtime client,
    including test doubles and slot overrides.
    """

    retry_policy = retry_policy or RetryPolicy()
    # The node name is the source of truth for slot resolution inside the
    # pipeline. This keeps nodes simple and prevents routing details from
    # leaking into every call site.
    slot = slot or get_node_text_slot(node)
    catalog_spec = spec or get_node_text_spec(node, generation_mode=generation_mode)
    effective_spec = effective_text_spec(catalog_spec=catalog_spec, model=model)
    effective_endpoint_host = (
        endpoint_host(effective_spec.base_url)
        if effective_spec.family == ModelFamily.OPENAI_COMPATIBLE
        else None
    )

    publish = _should_publish_events(generation_id)
    if not publish:
        logger.debug(
            "run_llm skipping event_bus (empty generation_id) node=%s slot=%s",
            node,
            slot.value,
        )

    attempt = 0
    while attempt < retry_policy.max_attempts:
        attempt += 1
        started_at = time.perf_counter()

        _publish_llm_event(
            generation_id,
            LLMCallStartedEvent(
                generation_id=generation_id or "",
                node=node,
                slot=slot.value,
                family=effective_spec.family.value,
                model_name=effective_spec.model_name,
                endpoint_host=effective_endpoint_host,
                attempt=attempt,
                section_id=section_id,
            ),
        )

        try:
            result = await agent.run(user_prompt=user_prompt)
            latency_ms = (time.perf_counter() - started_at) * 1000.0

            tokens_in, tokens_out = _extract_usage(result)
            cost_usd = _compute_cost_usd(effective_spec, tokens_in, tokens_out)

            _publish_llm_event(
                generation_id,
                LLMCallSucceededEvent(
                    generation_id=generation_id or "",
                    node=node,
                    slot=slot.value,
                    family=effective_spec.family.value,
                    model_name=effective_spec.model_name,
                    endpoint_host=effective_endpoint_host,
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
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            _publish_llm_event(
                generation_id,
                LLMCallFailedEvent(
                    generation_id=generation_id or "",
                    node=node,
                    slot=slot.value,
                    family=effective_spec.family.value,
                    model_name=effective_spec.model_name,
                    endpoint_host=effective_endpoint_host,
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
            can_retry = _is_retryable(exc) and attempt < retry_policy.max_attempts
            _publish_llm_event(
                generation_id,
                LLMCallFailedEvent(
                    generation_id=generation_id or "",
                    node=node,
                    slot=slot.value,
                    family=effective_spec.family.value,
                    model_name=effective_spec.model_name,
                    endpoint_host=effective_endpoint_host,
                    attempt=attempt,
                    section_id=section_id,
                    latency_ms=latency_ms,
                    retryable=can_retry,
                    error=str(exc),
                ),
            )
            if not can_retry:
                raise
            await asyncio.sleep(retry_policy.base_delay_seconds * attempt)

    raise RuntimeError("run_llm exhausted retries unexpectedly")
