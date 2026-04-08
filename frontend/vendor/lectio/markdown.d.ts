export declare function renderInlineMarkdown(text: string): string;
export declare function renderBlockMarkdown(text: string): string;
/**
 * Returns true if the string contains LaTeX control sequences.
 * Used to decide whether to send notation through KaTeX or render as prose.
 */
export declare function looksLikeLatex(text: string): boolean;
