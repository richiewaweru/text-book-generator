import { basePresets } from '../../presets/base-presets';
export const procedurePresetIds = [
    'blue-classroom',
    'warm-paper',
    'minimal-light'
];
export const procedurePresets = basePresets.filter((preset) => procedurePresetIds.includes(preset.id));
