import { basePresets } from '../../presets/base-presets';
export const classificationPresetIds = [
    'blue-classroom',
    'warm-paper',
    'high-contrast-focus'
];
export const classificationPresets = basePresets.filter((preset) => classificationPresetIds.includes(preset.id));
