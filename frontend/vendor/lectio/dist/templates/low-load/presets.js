import { basePresets } from '../../presets/base-presets';
export const lowLoadPresetIds = [
    'high-contrast-focus',
    'calm-green',
    'warm-paper',
    'minimal-light'
];
export const lowLoadPresets = basePresets.filter((preset) => lowLoadPresetIds.includes(preset.id));
