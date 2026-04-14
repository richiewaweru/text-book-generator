import { describe, expect, it } from 'vitest';

import { applyGenerationStreamEvent, type GenerationStreamContext } from './live-stream';

function createContext(overrides: Partial<GenerationStreamContext> = {}): GenerationStreamContext {
	return {
		document: null,
		plannedSections: null,
		qcSummary: null,
		progressUpdate: null,
		runtimePolicy: null,
		runtimeProgress: null,
		viewerWarning: null,
		activeSectionId: null,
		sectionSignals: {},
		...overrides
	};
}

describe('live-stream helpers', () => {
	it('normalizes runtime progress to media counters', () => {
		const result = applyGenerationStreamEvent(
			createContext(),
			'runtime_progress',
			JSON.stringify({
				type: 'runtime_progress',
				generation_id: 'gen-1',
				snapshot: {
					mode: 'balanced',
					sections_total: 2,
					sections_completed: 0,
					sections_running: 1,
					sections_queued: 1,
					diagram_running: 1,
					diagram_queued: 0,
					qc_running: 0,
					qc_queued: 0,
					retry_running: 0,
					retry_queued: 0
				},
				emitted_at: '2026-04-14T00:00:00Z'
			})
		);

		expect(result.next.runtimeProgress?.media_running).toBe(1);
		expect(result.next.runtimeProgress?.media_queued).toBe(0);
	});

	it('tracks required media blocks at section level', () => {
		const result = applyGenerationStreamEvent(
			createContext(),
			'section_media_blocked',
			JSON.stringify({
				type: 'section_media_blocked',
				generation_id: 'gen-1',
				section_id: 's-01',
				slot_ids: ['diagram-main'],
				reason: 'Required media is still incomplete.',
				blocked_at: '2026-04-14T00:00:00Z'
			})
		);

		expect(result.next.sectionSignals['s-01']).toEqual({
			status: 'blocked_by_required_media',
			reason: 'Required media is still incomplete.',
			slot_ids: ['diagram-main']
		});
	});
});
