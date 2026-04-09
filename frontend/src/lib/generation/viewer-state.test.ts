import { describe, expect, it } from 'vitest';

import {
	applySectionFailed,
	applySectionReady,
	applySectionStarted,
	buildSectionSlots,
	normalizeDocument
} from './viewer-state';
import type { GenerationDocument } from '$lib/types';

const firstSection = {
	section_id: 's-01',
	template_id: 'guided-concept-path',
	header: {
		title: 'First section',
		subject: 'Calculus',
		grade_band: 'secondary'
	},
	hook: {
		headline: 'Start here',
		body: 'Look at nearby behavior.',
		anchor: 'limits'
	},
	explanation: {
		body: 'Limits study nearby behavior.',
		emphasis: ['nearby behavior']
	},
	practice: {
		problems: [
			{
				difficulty: 'warm',
				question: 'What happens near x = 2?',
				hints: [{ level: 1, text: 'Look near 2.' }]
			},
			{
				difficulty: 'medium',
				question: 'Estimate the limit of x^2 near 2.',
				hints: [{ level: 1, text: 'Square numbers near 2.' }]
			}
		]
	},
	what_next: {
		body: 'Now connect this to continuity.',
		next: 'Continuity'
	}
};

const secondSection = {
	...firstSection,
	section_id: 's-02',
	header: {
		...firstSection.header,
		title: 'Second section'
	}
};

function createDocument(overrides: Partial<GenerationDocument> = {}): GenerationDocument {
	return {
		generation_id: 'gen-123',
		subject: 'Calculus',
		context: 'Explain limits',
		mode: 'balanced',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		status: 'running',
		section_manifest: [],
		sections: [],
		failed_sections: [],
		qc_reports: [],
		quality_passed: null,
		error: null,
		created_at: '2026-03-19T00:00:00Z',
		updated_at: '2026-03-19T00:00:00Z',
		completed_at: null,
		...overrides
	};
}

describe('viewer-state helpers', () => {
	it('records section_started metadata in manifest order', () => {
		const next = applySectionStarted(
			applySectionStarted(createDocument(), {
				type: 'section_started',
				generation_id: 'gen-123',
				section_id: 's-02',
				title: 'Second section',
				position: 2
			}),
			{
				type: 'section_started',
				generation_id: 'gen-123',
				section_id: 's-01',
				title: 'First section',
				position: 1
			}
		);

		expect(next.section_manifest.map((item) => item.section_id)).toEqual(['s-01', 's-02']);
	});

	it('keeps ready sections in manifest order even if they arrive out of order', () => {
		const document = normalizeDocument(
			createDocument({
				section_manifest: [
					{ section_id: 's-01', title: 'First section', position: 1 },
					{ section_id: 's-02', title: 'Second section', position: 2 }
				]
			})
		);

		const afterSecond = applySectionReady(document, {
			section_id: 's-02',
			section: secondSection as any
		}).document;
		const afterFirst = applySectionReady(afterSecond, {
			section_id: 's-01',
			section: firstSection as any
		}).document;

		expect(afterFirst.sections.map((section) => section.section_id)).toEqual(['s-01', 's-02']);
	});

	it('skips invalid sections and returns a non-fatal warning', () => {
		const document = createDocument();
		const result = applySectionReady(document, {
			section_id: 's-01',
			section: {
				...firstSection,
				what_next: { body: 'Missing next value' }
			} as any
		});

		expect(result.document.sections).toHaveLength(0);
		expect(result.warning?.message).toMatch(/Invalid section from pipeline/);
	});

	it('builds ordered completed and queued slots from persisted manifest metadata', () => {
		const slots = buildSectionSlots(
			createDocument({
				section_manifest: [
					{ section_id: 's-01', title: 'First section', position: 1 },
					{ section_id: 's-02', title: 'Second section', position: 2 },
					{ section_id: 's-03', title: 'Third section', position: 3 }
				],
				sections: [secondSection as any]
			}),
			3
		);

		expect(slots.map((slot) => `${slot.position}:${slot.status}:${slot.title}`)).toEqual([
			'1:queued:First section',
			'2:completed:Second section',
			'3:queued:Third section'
		]);
	});

	it('marks failed sections in slots and document state', () => {
		const document = createDocument({
			section_manifest: [
				{ section_id: 's-01', title: 'First section', position: 1 },
				{ section_id: 's-02', title: 'Second section', position: 2 }
			]
		});
		const failed = applySectionFailed(document, {
			type: 'section_failed',
			generation_id: 'gen-123',
			section_id: 's-02',
			title: 'Second section',
			position: 2,
			failed_at_node: 'content_generator',
			error_type: 'validation',
			error_summary: 'Schema validation failed.',
			needs_diagram: false,
			needs_worked_example: false,
			attempt_count: 1,
			can_retry: true,
			missing_components: ['section-header'],
			timestamp: new Date().toISOString()
		});

		const slots = buildSectionSlots(failed, 2);
		expect(failed.failed_sections).toHaveLength(1);
		expect(slots.map((slot) => `${slot.position}:${slot.status}:${slot.title}`)).toEqual([
			'1:queued:First section',
			'2:failed:Second section'
		]);
	});
});
