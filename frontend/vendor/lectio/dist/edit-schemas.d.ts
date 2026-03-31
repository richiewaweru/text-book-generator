export type FieldInputType = 'text' | 'textarea' | 'richtext' | 'number' | 'select' | 'list' | 'object-list' | 'boolean' | 'media' | 'svg' | 'hidden';
export interface FieldSchema {
    field: string;
    label: string;
    input: FieldInputType;
    required: boolean;
    placeholder?: string;
    maxWords?: number;
    maxItems?: number;
    options?: Array<{
        value: string;
        label: string;
    }>;
    itemSchema?: FieldSchema[];
    help?: string;
}
export interface EditSchema {
    component_id: string;
    fields: FieldSchema[];
}
/**
 * Edit schema for builder forms. Null when the component has no block field (e.g. glossary-inline).
 */
export declare function getEditSchema(componentId: string): EditSchema | null;
