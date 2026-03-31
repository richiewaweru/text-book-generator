import type { TemplateDefinition, TemplateFilters } from './template-types';
export declare const templateRegistry: TemplateDefinition[];
export declare const templateRegistryMap: {
    [k: string]: TemplateDefinition;
};
export declare function getTemplateById(templateId: string): TemplateDefinition;
export declare function filterTemplates(filters: TemplateFilters): TemplateDefinition[];
export declare function getTemplateFamilies(): import("./template-types").TemplateFamily[];
export declare function validateAllTemplates(): {
    errors: string[];
    warnings: string[];
    id: string;
}[];
