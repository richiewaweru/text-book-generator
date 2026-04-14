import type {
	ErrorEvent,
	GenerationDocument,
	MediaFrameFailedEvent,
	MediaFrameReadyEvent,
	MediaFrameStartedEvent,
	MediaPlanReadyEvent,
	MediaSlotFailedEvent,
	MediaSlotReadyEvent,
	ProgressUpdateEvent,
	QCCompleteEvent,
	RuntimePolicyEvent,
	RuntimeProgressEvent,
	SectionAssetPendingEvent,
	SectionAssetReadyEvent,
	SectionFailedEvent,
	SectionFinalEvent,
	SectionMediaBlockedEvent,
	SectionPartialEvent,
	SectionReadyEvent,
	SectionStartedEvent
} from '$lib/types';

import {
	applySectionAssetPending,
	applySectionAssetReady,
	applySectionFailed,
	applySectionFinal,
	applySectionPartial,
	applySectionReady,
	applySectionStarted,
	type ViewerSectionSignal
} from './viewer-state';

export interface GenerationStreamContext {
	document: GenerationDocument | null;
	plannedSections: number | null;
	qcSummary: { passed: number; total: number } | null;
	progressUpdate: ProgressUpdateEvent | null;
	runtimePolicy: RuntimePolicyEvent | null;
	runtimeProgress: RuntimeProgressEvent['snapshot'] | null;
	viewerWarning: string | null;
	activeSectionId: string | null;
	sectionSignals: Record<string, ViewerSectionSignal>;
}

export interface GenerationStreamOutcome {
	next: GenerationStreamContext;
	terminal:
		| {
				kind: 'complete' | 'generation_failed' | 'error';
				message?: string | null;
		  }
		| null;
}

function setSectionSignal(
	signals: Record<string, ViewerSectionSignal>,
	sectionId: string,
	signal: ViewerSectionSignal
): Record<string, ViewerSectionSignal> {
	return {
		...signals,
		[sectionId]: signal
	};
}

function normalizeRuntimeProgressSnapshot(
	snapshot: RuntimeProgressEvent['snapshot'] & { diagram_running?: number; diagram_queued?: number }
): RuntimeProgressEvent['snapshot'] {
	return {
		...snapshot,
		media_running: snapshot.media_running ?? snapshot.diagram_running ?? 0,
		media_queued: snapshot.media_queued ?? snapshot.diagram_queued ?? 0
	};
}

function normalizeRuntimePolicyEvent(
	event: RuntimePolicyEvent & {
		concurrency: RuntimePolicyEvent['concurrency'] & { max_diagram_concurrency?: number };
	}
): RuntimePolicyEvent {
	return {
		...event,
		concurrency: {
			...event.concurrency,
			max_media_concurrency:
				event.concurrency.max_media_concurrency ?? event.concurrency.max_diagram_concurrency ?? 0
		}
	};
}

function applyMediaFrameSignal(
	context: GenerationStreamContext,
	payload: MediaFrameStartedEvent | MediaFrameReadyEvent | MediaFrameFailedEvent
): GenerationStreamContext {
	const current = context.sectionSignals[payload.section_id];
	const status: ViewerSectionSignal =
		payload.type === 'media_frame_started'
			? { status: 'generating' }
			: payload.type === 'media_frame_ready'
				? { status: 'partially_ready' }
				: current ?? { status: 'partially_ready' };

	return {
		...context,
		activeSectionId:
			payload.type === 'media_frame_started' ? payload.section_id : context.activeSectionId,
		sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, status)
	};
}

export function applyGenerationStreamEvent(
	context: GenerationStreamContext,
	type: string,
	data: string
): GenerationStreamOutcome {
	switch (type) {
		case 'pipeline_start': {
			const payload = JSON.parse(data) as { section_count: number };
			return {
				next: { ...context, plannedSections: payload.section_count },
				terminal: null
			};
		}
		case 'progress_update': {
			const payload = JSON.parse(data) as ProgressUpdateEvent;
			return {
				next: {
					...context,
					progressUpdate: payload,
					activeSectionId: payload.section_id ?? context.activeSectionId
				},
				terminal: null
			};
		}
		case 'runtime_policy': {
			const payload = normalizeRuntimePolicyEvent(JSON.parse(data) as RuntimePolicyEvent);
			return {
				next: { ...context, runtimePolicy: payload },
				terminal: null
			};
		}
		case 'runtime_progress': {
			const payload = JSON.parse(data) as RuntimeProgressEvent;
			return {
				next: {
					...context,
					runtimeProgress: normalizeRuntimeProgressSnapshot(payload.snapshot),
					plannedSections: context.plannedSections ?? payload.snapshot.sections_total
				},
				terminal: null
			};
		}
		case 'section_started': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionStartedEvent;
			return {
				next: {
					...context,
					document: applySectionStarted(context.document, payload),
					activeSectionId: payload.section_id,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'generating'
					})
				},
				terminal: null
			};
		}
		case 'media_plan_ready': {
			const payload = JSON.parse(data) as MediaPlanReadyEvent;
			return {
				next: {
					...context,
					sectionSignals: setSectionSignal(
						context.sectionSignals,
						payload.section_id,
						context.sectionSignals[payload.section_id] ?? { status: 'planned' }
					)
				},
				terminal: null
			};
		}
		case 'media_frame_started':
		case 'media_frame_ready':
		case 'media_frame_failed': {
			return {
				next: applyMediaFrameSignal(
					context,
					JSON.parse(data) as MediaFrameStartedEvent | MediaFrameReadyEvent | MediaFrameFailedEvent
				),
				terminal: null
			};
		}
		case 'media_slot_ready': {
			const payload = JSON.parse(data) as MediaSlotReadyEvent;
			return {
				next: {
					...context,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready'
					})
				},
				terminal: null
			};
		}
		case 'media_slot_failed': {
			const payload = JSON.parse(data) as MediaSlotFailedEvent;
			return {
				next: {
					...context,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready',
						reason: payload.error ?? null,
						slot_ids: [payload.slot_id]
					})
				},
				terminal: null
			};
		}
		case 'section_media_blocked': {
			const payload = JSON.parse(data) as SectionMediaBlockedEvent;
			return {
				next: {
					...context,
					activeSectionId:
						context.activeSectionId === payload.section_id ? null : context.activeSectionId,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'blocked_by_required_media',
						reason: payload.reason,
						slot_ids: payload.slot_ids
					})
				},
				terminal: null
			};
		}
		case 'section_partial': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionPartialEvent;
			const result = applySectionPartial(context.document, payload);
			return {
				next: {
					...context,
					document: result.document,
					viewerWarning: result.warning?.message ?? context.viewerWarning,
					activeSectionId: payload.section_id,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready'
					})
				},
				terminal: null
			};
		}
		case 'section_asset_pending': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionAssetPendingEvent;
			return {
				next: {
					...context,
					document: applySectionAssetPending(context.document, payload),
					activeSectionId: payload.section_id,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready'
					})
				},
				terminal: null
			};
		}
		case 'section_asset_ready': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionAssetReadyEvent;
			return {
				next: {
					...context,
					document: applySectionAssetReady(context.document, payload),
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready'
					})
				},
				terminal: null
			};
		}
		case 'section_final': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionFinalEvent;
			return {
				next: {
					...context,
					document: applySectionFinal(context.document, payload),
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'partially_ready'
					})
				},
				terminal: null
			};
		}
		case 'section_ready': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionReadyEvent;
			const result = applySectionReady(context.document, payload);
			return {
				next: {
					...context,
					document: result.document,
					plannedSections: payload.total_sections,
					viewerWarning: result.warning?.message ?? context.viewerWarning,
					activeSectionId:
						context.activeSectionId === payload.section_id ? null : context.activeSectionId,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'ready'
					})
				},
				terminal: null
			};
		}
		case 'section_failed': {
			if (!context.document) return { next: context, terminal: null };
			const payload = JSON.parse(data) as SectionFailedEvent;
			return {
				next: {
					...context,
					document: applySectionFailed(context.document, payload),
					activeSectionId:
						context.activeSectionId === payload.section_id ? null : context.activeSectionId,
					sectionSignals: setSectionSignal(context.sectionSignals, payload.section_id, {
						status: 'failed'
					})
				},
				terminal: null
			};
		}
		case 'qc_complete': {
			const payload = JSON.parse(data) as QCCompleteEvent;
			return {
				next: {
					...context,
					qcSummary: { passed: payload.passed, total: payload.total }
				},
				terminal: null
			};
		}
		case 'complete':
			return { next: context, terminal: { kind: 'complete' } };
		case 'generation_failed': {
			const payload = JSON.parse(data) as { message: string };
			return {
				next: context,
				terminal: { kind: 'generation_failed', message: payload.message }
			};
		}
		case 'error': {
			const payload = JSON.parse(data) as ErrorEvent;
			return {
				next: context,
				terminal: { kind: 'error', message: payload.message }
			};
		}
		default:
			return { next: context, terminal: null };
	}
}
