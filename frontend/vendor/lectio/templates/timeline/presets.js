import { basePresets } from '../../presets/base-presets';
export const timelinePresetIds = [
    'warm-paper',
    'blue-classroom',
    'minimal-light'
];
export const timelinePresets = basePresets.filter((preset) => timelinePresetIds.includes(preset.id));
