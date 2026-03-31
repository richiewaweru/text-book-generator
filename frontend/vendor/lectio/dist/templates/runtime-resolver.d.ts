import type { TemplateDefinition, TemplatePresetDefinition } from '../template-types';
export declare const DEFAULT_PRESET_ID = "warm-paper";
export declare function resolveTemplateDefinition(templateId: string): TemplateDefinition;
export declare function resolveTemplatePreset(definition: TemplateDefinition, presetId?: string): TemplatePresetDefinition | null;
