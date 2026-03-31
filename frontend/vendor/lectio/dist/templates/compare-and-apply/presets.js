import { basePresets } from '../../presets/base-presets';
export const compareAndApplyPresetIds = [
    'blue-classroom',
    'warm-paper',
    'high-contrast-focus'
];
export const compareAndApplyPresets = basePresets.filter((preset) => compareAndApplyPresetIds.includes(preset.id));
