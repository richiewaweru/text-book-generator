from textbook_agent.domain.entities.textbook import RawTextbook


class HTMLRenderer:
    """Renders a RawTextbook into a self-contained HTML file.

    Pure Python - no LLM calls. Uses the design system from base.css.
    All intelligence lives in the pipeline nodes; this is mechanical assembly.
    """

    def render(self, textbook: RawTextbook) -> str:
        raise NotImplementedError
