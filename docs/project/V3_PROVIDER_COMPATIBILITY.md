# V3 Provider Compatibility

This note is the source of truth for provider-specific structured-output behavior in
the V3 pipeline and block-generation surfaces.

## Baseline posture

- Anthropic is the default baseline when no `V3_*` slot overrides are set.
- OpenAI-compatible providers such as DeepSeek are opt-in through
  `V3_FAST_*`, `V3_STANDARD_*`, and `V3_PREMIUM_*`.
- Nodes declare only their schema and slot; provider quirks are handled centrally.

## DeepSeek live model ID

- The live DeepSeek API model name is `deepseek-flash` (DeepSeek-V4.1-Flash).
- Use `deepseek-flash` for `V3_FAST_MODEL_NAME`, `V3_STANDARD_MODEL_NAME`, and
  `V3_PREMIUM_MODEL_NAME`. Slot quality still comes from the per-node thinking
  policy, not from separate Flash vs Pro model IDs.
- Legacy names `deepseek-v4-flash` and `deepseek-v4-pro` are temporary compatibility
  aliases; prefer `deepseek-flash` in new config.

## Thinking mode

- DeepSeek Chat Completions thinking is **enabled by default** (default effort
  `high`).
- Nodes with a string `V3_NODE_REASONING` policy send
  `openai_reasoning_effort` plus `extra_body.thinking.type=enabled`.
- Nodes with `V3_NODE_REASONING=False` must send
  `extra_body.thinking.type=disabled`; omitting the flag leaves thinking on.
- Effort values are `low` / `high` / `max` on the first-party API. Our internal
  `"medium"` maps to DeepSeek `high`.
- Reasoning text arrives in `reasoning_content`; usage may report
  `reasoning_tokens`. Keep the `openai_chat_thinking_field="reasoning_content"`
  profile for any `deepseek-*` model name.

## Structured output policy

- Anthropic keeps the normal structured-output path used by `pydantic_ai`.
- DeepSeek thinking models must avoid `tool_choice` structured output.
- For DeepSeek-style OpenAI-compatible thinking nodes, V3 uses prompted JSON instead
  of tool/native structured output.

The central decision point is
`backend/src/v3_execution/llm_helpers.py::structured_output_type_for_model(...)`.

## Where the policy applies today

- V3 Studio helpers: `signals`, `narrow`, `blueprint_adjust`
- V3 planning: `stage1_planner`, `stage2_expander`
- Block generation paths that use structured schema output

When adding a new structured-output node, route it through the shared helper instead
of adding provider-specific branching in the route or prompt.

## Operational guidance

- To keep Anthropic as the deployment baseline, leave `V3_*` slot overrides unset.
- To run DeepSeek, set the `V3_*` slot overrides plus `DEEPSEEK_API_KEY`, using
  `deepseek-flash` as the model name on each slot.
- Visual QC remains on its Anthropic node default even when DeepSeek overrides
  the FAST slot.
- If a new OpenAI-compatible provider is introduced later, add its compatibility
  behavior in the shared helper rather than forking individual node code.
