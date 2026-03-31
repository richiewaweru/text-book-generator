import type { GradeBand, SectionContent } from './types';
/** Portable lesson document format version. Bump on breaking changes. */
export type LessonDocumentVersion = 1;
export interface BlockInstance {
    id: string;
    component_id: string;
    content: Record<string, unknown>;
    position: number;
}
export interface DocumentSection {
    id: string;
    template_id: string;
    block_ids: string[];
    title: string;
    position: number;
}
export interface MediaReference {
    id: string;
    type: 'video' | 'image' | 'audio';
    url: string;
    filename?: string;
    mime_type?: string;
    alt_text?: string;
    print_fallback?: 'thumbnail' | 'qr-link' | 'hide';
}
export interface LessonDocument {
    version: LessonDocumentVersion;
    id: string;
    title: string;
    subject: string;
    description?: string;
    preset_id: string;
    source: 'generated' | 'template' | 'manual';
    source_generation_id?: string;
    grade_band?: GradeBand;
    sections: DocumentSection[];
    blocks: Record<string, BlockInstance>;
    media: Record<string, MediaReference>;
    created_at: string;
    updated_at: string;
    author?: string;
}
export interface DocumentValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}
export interface FromSectionContentsMetadata {
    title: string;
    subject: string;
    preset_id: string;
    /** Fallback when a section lacks template_id (rare) */
    template_id?: string;
    source?: 'generated' | 'template' | 'manual';
    source_generation_id?: string;
    grade_band?: GradeBand;
}
/**
 * Field name → component registry id. Inverse of getComponentFieldMap().
 * Only keys that map to a block component appear.
 */
export declare function getFieldComponentMap(): Partial<Record<keyof SectionContent, string>>;
/**
 * Decompose SectionContent[] into a LessonDocument.
 * Preserves section_id as DocumentSection.id for stable round-trips.
 */
export declare function fromSectionContents(sections: SectionContent[], metadata: FromSectionContentsMetadata): LessonDocument;
/**
 * Rebuild SectionContent[] from a LessonDocument (for rendering / validation).
 */
export declare function toSectionContents(document: LessonDocument): SectionContent[];
/**
 * Structural + capacity validation. Structural problems set valid=false.
 */
export declare function validateDocument(document: LessonDocument): DocumentValidationResult;
