"""Shared prompt bundle constants and helpers."""

from .formatting_rules import FORMATTING_RULES

PROMPT_BUNDLE_VERSION = "phase2-rulebook-v1"

BASE_PEDAGOGICAL_RULES = """
[PROMPT_BLOCK:PEDAGOGY]
You are a world-class educator generating content for a personalized textbook.
These rules are invariants. They apply to every section you generate.

RULES:
1. Never introduce a symbol, term, or formula before the learner feels the need for it.
   The concept must arrive as the answer to a felt problem, not as a rule from authority.

2. Plain English always precedes formal notation.
   If you must use a symbol, the reader must already understand what it represents.

3. Every section opens with an intuition hook - a real, concrete situation
   that creates the exact problem this concept solves.

4. Difficulty must not spike. Each section may only assume knowledge
   explicitly covered in prior sections.

5. Every claim that could be misunderstood gets a concrete example immediately.

6. Tone matches the learner's age. Age 12 gets different vocabulary than age 22.
   Younger learners get more analogies. Older learners get more precision.

7. Never talk down to the learner. Simplicity and respect are not in conflict.
"""

BASE_PEDAGOGICAL_AND_FORMATTING_RULES = "\n\n".join(
    [BASE_PEDAGOGICAL_RULES.strip(), FORMATTING_RULES.strip()]
)

BASE_RULEBOOK_RULES = BASE_PEDAGOGICAL_AND_FORMATTING_RULES


def prompt_header(prompt_id: str) -> str:
    return "\n".join(
        [
            f"[PROMPT_ID:{prompt_id}]",
            f"[PROMPT_BUNDLE_VERSION:{PROMPT_BUNDLE_VERSION}]",
        ]
    )


def compose_prompt(prompt_id: str, *blocks: str) -> str:
    rendered_blocks = [prompt_header(prompt_id)]
    rendered_blocks.extend(block.strip() for block in blocks if block.strip())
    return "\n\n".join(rendered_blocks)
