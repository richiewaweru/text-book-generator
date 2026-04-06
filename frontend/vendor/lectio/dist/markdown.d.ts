/**
 * Inline markdown → HTML.
 * Covers **bold**, *italic*, `code`.
 * Safe for {@html} — input is LLM-generated structured content, not arbitrary user HTML.
 */
export declare function renderInlineMarkdown(text: string): string;
/**
 * Block markdown → HTML.
 * Extends inline with paragraph breaks and HR.
 * Use only for ExplanationBlock.body — the one field that legitimately spans multiple paragraphs.
 */
export declare function renderBlockMarkdown(text: string): string;
/**
 * Returns true if the string contains LaTeX control sequences.
 * Used to decide whether to send notation through KaTeX or render as prose.
 */
export declare function looksLikeLatex(text: string): boolean;
