/**
 * Valid placeholder content for a component. Required fields use empty or minimal values.
 */
export declare function getEmptyContent(componentId: string): Record<string, unknown>;
/**
 * Richer demo content for palette previews. Extend per-component as needed.
 */
export declare function getPreviewContent(componentId: string): Record<string, unknown> | null;
/** Every component with a section field must have a factory (builder + document conversion). */
export declare function assertFactoriesCoverRegistry(): void;
