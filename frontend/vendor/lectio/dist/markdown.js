function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
/**
 * Inline markdown → HTML.
 * Covers **bold**, *italic*, `code`.
 * Safe for {@html} — input is LLM-generated structured content, not arbitrary user HTML.
 */
export function renderInlineMarkdown(text) {
    if (!text)
        return '';
    return escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/_(.+?)_/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code class="rounded bg-muted px-1 text-[0.85em]">$1</code>');
}
/**
 * Block markdown → HTML.
 * Extends inline with paragraph breaks and HR.
 * Use only for ExplanationBlock.body — the one field that legitimately spans multiple paragraphs.
 */
export function renderBlockMarkdown(text) {
    if (!text)
        return '';
    const withInline = renderInlineMarkdown(text);
    return withInline
        .replace(/^---$/gm, '<hr class="my-4 border-border/40" />')
        .replace(/\n\n+/g, '</p><p class="mt-4 text-base leading-7 text-foreground/84">');
}
/**
 * Returns true if the string contains LaTeX control sequences.
 * Used to decide whether to send notation through KaTeX or render as prose.
 */
export function looksLikeLatex(text) {
    return /[\\^_{}\[\]]|\\[a-zA-Z]/.test(text);
}
