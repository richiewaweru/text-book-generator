import type { CanvasSection } from '$lib/types/v3';

import { mergeComponentField } from '$lib/studio/v3-canvas';

type StreamApplyResult = {
	canvas: CanvasSection[];
	warning: string | null;
};

function asRecord(raw: unknown): Record<string, unknown> {
	return typeof raw === 'object' && raw !== null
		? (raw as Record<string, unknown>)
		: { value: raw ?? null };
}

function markComponentFailed(
	canvas: CanvasSection[],
	sectionId: string,
	componentId: string,
	data: Record<string, unknown>
): CanvasSection[] {
	return canvas.map((s) =>
		s.id !== sectionId
			? s
			: {
					...s,
					components: s.components.map((c) =>
						c.id === componentId ? { ...c, status: 'failed' as const, data } : c
					)
				}
	);
}

export function applyComponentReadyToCanvas(
	canvas: CanvasSection[],
	payload: Record<string, unknown>
): StreamApplyResult {
	const sectionId = String(payload.section_id ?? '');
	const componentId = String(payload.component_id ?? '');
	const sectionField = String(payload.section_field ?? '');
	const data = asRecord(payload.data);

	if (!sectionId || !componentId) {
		return {
			canvas,
			warning: 'Generation event missing section/component identity.'
		};
	}
	if (!sectionField) {
		return {
			canvas: markComponentFailed(canvas, sectionId, componentId, data),
			warning: 'A component response arrived without section mapping (section_field).'
		};
	}
	return {
		canvas: canvas.map((s) =>
			s.id !== sectionId
				? s
				: {
						...s,
						mergedFields: mergeComponentField(s.mergedFields, sectionField, data),
						components: s.components.map((c) =>
							c.id === componentId ? { ...c, status: 'ready' as const, data } : c
						)
					}
		),
		warning: null
	};
}

export function applyComponentPatchedToCanvas(
	canvas: CanvasSection[],
	payload: Record<string, unknown>
): StreamApplyResult {
	const sectionId = String(payload.section_id ?? '');
	const componentId = String(payload.component_id ?? '');
	const sectionField = String(payload.section_field ?? '');
	const data = asRecord(payload.data);

	if (!sectionId || !componentId) {
		return {
			canvas,
			warning: 'Repair event missing section/component identity.'
		};
	}
	if (!sectionField) {
		return {
			canvas: markComponentFailed(canvas, sectionId, componentId, data),
			warning: 'A repaired component arrived without section mapping (section_field).'
		};
	}
	return {
		canvas: canvas.map((s) =>
			s.id !== sectionId
				? s
				: {
						...s,
						mergedFields: mergeComponentField(s.mergedFields, sectionField, data),
						components: s.components.map((c) =>
							c.id === componentId ? { ...c, status: 'patched' as const, data } : c
						)
					}
		),
		warning: null
	};
}

export function applySectionWriterFailedToCanvas(
	canvas: CanvasSection[],
	payload: Record<string, unknown>
): StreamApplyResult {
	const sectionId = String(payload.section_id ?? '');
	if (!sectionId) {
		return {
			canvas,
			warning: 'Section writer failure event missing section id.'
		};
	}
	const failure = {
		errors: Array.isArray(payload.errors) ? payload.errors : [],
		warnings: Array.isArray(payload.warnings) ? payload.warnings : []
	};
	return {
		canvas: canvas.map((s) =>
			s.id !== sectionId
				? s
				: {
						...s,
						components: s.components.map((c) => ({
							...c,
							status: 'failed' as const,
							data: c.data ?? failure
						}))
					}
		),
		warning: `Section ${sectionId} failed during generation.`
	};
}

