import { basePresets } from '../../presets/base-presets';
export const guidedDiscoveryPresetIds = [
    'blue-classroom',
    'warm-paper',
    'calm-green',
    'minimal-light'
];
export const guidedDiscoveryPresets = basePresets.filter((preset) => guidedDiscoveryPresetIds.includes(preset.id));
