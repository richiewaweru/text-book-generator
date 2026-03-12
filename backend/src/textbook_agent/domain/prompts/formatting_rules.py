"""Formatting invariants injected into every content-generating node."""

FORMATTING_RULES = """
[PROMPT_BLOCK:FORMATTING]
Formatting and presentation rules are invariants. They apply to every section you generate.

[PROMPT:TYPOGRAPHY]
- Use emphasis sparingly. Do not bold more than once per paragraph.
- Do not use exclamation marks in body prose.
- Keep prose readable and sentence lengths controlled.

[PROMPT:NOTATION]
- Use one symbol per concept and keep that symbol consistent throughout the section.
- Put spaces around binary operators such as +, -, =, <, and >.
- Use proper HTML subscript or superscript markup instead of Unicode subscript or superscript characters.
- Use inline math for short expressions and display math only for multi-step or focal equations.

[PROMPT:CALLOUTS]
- Start every section with exactly one intuition hook.
- Include at most one pitfall or misconception block per section.
- Keep pitfall text to four sentences or fewer.
- Do not nest callouts inside other callouts.

[PROMPT:CONTENT_STRUCTURE]
- Return JSON only and match the schema exactly.
- Populate SectionContent fields in this order: section_id, hook, prerequisites_block, plain_explanation, formal_definition, worked_example, common_misconception, practice_problems, interview_anchor, think_prompt, connection_forward.
- Maintain heading hierarchy mentally as H1 once for the textbook, H2 for sections, H3 for subsections, and H4 for labels.

[PROMPT:TABLES]
- Put the table title above the table.
- Always include a header row.
- Limit tables to six columns.
- Put measurement units in headers, not in body cells.

[PROMPT:CODE]
- Keep code lines at or under 80 characters.
- Comments explain why, not what.
- Aim for roughly one meaningful comment every three to five lines when comments are needed.
- Do not include commented-out code.

[PROMPT:WORKED_EXAMPLES]
- Explain why each step is taken, not only what changed.
- Use a clear sequential flow.
- End with an explicit conclusion sentence.

[PROMPT:PRACTICE]
- Provide exactly three practice problems per section.
- Use one warm, one medium, and one cold difficulty item.
- Each problem needs a genuine hint.
- Do not include full solutions in the body.
"""
