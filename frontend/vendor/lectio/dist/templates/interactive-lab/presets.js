import { basePresets } from '../../presets/base-presets';
export const interactiveLabPresetIds = [
    'blue-classroom',
    'warm-paper',
    'calm-green',
    'high-contrast-focus'
];
export const interactiveLabPresets = basePresets.filter((preset) => interactiveLabPresetIds.includes(preset.id));
