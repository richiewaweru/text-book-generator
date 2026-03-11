import json
import re


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response text, stripping markdown code fences if present."""
    stripped = text.strip()

    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    match = fence_pattern.search(stripped)
    if match:
        stripped = match.group(1).strip()

    return json.loads(stripped)
