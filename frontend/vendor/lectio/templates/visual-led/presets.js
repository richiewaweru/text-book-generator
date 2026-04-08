import { basePresets } from '../../presets/base-presets';
export const visualLedPresetIds = [
    'calm-green',
    'blue-classroom',
    'high-contrast-focus'
];
export const visualLedPresets = basePresets.filter((preset) => visualLedPresetIds.includes(preset.id));
