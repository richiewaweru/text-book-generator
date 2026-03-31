import { basePresets } from '../../presets/base-presets';
export const diagramLedPresetIds = [
    'calm-green',
    'blue-classroom',
    'warm-paper'
];
export const diagramLedPresets = basePresets.filter((preset) => diagramLedPresetIds.includes(preset.id));
