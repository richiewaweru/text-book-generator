import { basePresets } from '../../presets/base-presets';
export const guidedConceptPathPresetIds = [
    'blue-classroom',
    'warm-paper',
    'calm-green',
    'high-contrast-focus'
];
export const guidedConceptPathPresets = basePresets.filter((preset) => guidedConceptPathPresetIds.includes(preset.id));
