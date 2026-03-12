import json
import re
from copy import deepcopy


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response text, stripping markdown code fences if present."""
    stripped = text.strip()

    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    match = fence_pattern.search(stripped)
    if match:
        stripped = match.group(1).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[index:])
            return parsed
        except json.JSONDecodeError:
            continue

    return json.loads(stripped)


def to_strict_json_schema(schema: dict) -> dict:
    """Normalize a JSON schema for OpenAI strict structured outputs."""

    def visit(node, *, in_properties: bool = False):
        if isinstance(node, dict):
            for key in list(node.keys()):
                if key == "default":
                    node.pop(key, None)
                    continue
                if key == "title" and not in_properties:
                    node.pop(key, None)
                    continue
                if key == "properties":
                    visit(node[key], in_properties=True)
                else:
                    visit(node[key], in_properties=False)

            if node.get("type") == "object" or "properties" in node:
                node.setdefault("additionalProperties", False)
                if "properties" in node:
                    node["required"] = list(node["properties"].keys())
        elif isinstance(node, list):
            for item in node:
                visit(item, in_properties=False)

    normalized = deepcopy(schema)
    visit(normalized)
    return normalized
