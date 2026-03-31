import { basePresets } from '../../presets/base-presets';
export const conceptCompactPresetIds = [
    'blue-classroom',
    'warm-paper',
    'minimal-light'
];
export const conceptCompactPresets = basePresets.filter((preset) => conceptCompactPresetIds.includes(preset.id));
