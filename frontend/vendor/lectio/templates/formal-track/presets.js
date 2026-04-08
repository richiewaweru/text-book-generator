import { basePresets } from '../../presets/base-presets';
export const formalTrackPresetIds = ['warm-paper', 'minimal-light'];
export const formalTrackPresets = basePresets.filter((preset) => formalTrackPresetIds.includes(preset.id));
