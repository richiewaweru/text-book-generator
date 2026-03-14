import type { GenerationMode, GenerationProgress, GenerationStatus } from '$lib/types';

export function resolveGenerationMode(status: GenerationStatus): GenerationMode | null {
	return status.progress?.mode ?? status.result?.mode ?? status.mode ?? null;
}

export function progressPercent(progress: GenerationProgress | null): number {
	if (!progress?.sections_total || progress.sections_total <= 0) {
		return 0;
	}
	return Math.max(0, Math.min(100, Math.round((progress.sections_completed / progress.sections_total) * 100)));
}

export function hasRetryContext(progress: GenerationProgress | null): boolean {
	return Boolean(progress?.retry_attempt && progress.retry_limit);
}
