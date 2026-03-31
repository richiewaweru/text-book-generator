// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { generationState } from '$lib/stores/studio';

const { getGenerationDetail, getGenerationDocument, buildGenerationEventsUrl } = vi.hoisted(() => ({
	getGenerationDetail: vi.fn(),
	getGenerationDocument: vi.fn(),
	buildGenerationEventsUrl: vi.fn((id: string) => `/api/v1/generations/${id}/events`)
}));

vi.mock('$lib/api/client', () => ({
	getGenerationDetail,
	getGenerationDocument,
	buildGenerationEventsUrl
}));

import GenerationView from './GenerationView.svelte';

class MockEventSource {
	static instances: MockEventSource[] = [];

	url: string;
	closed = false;
	private listeners = new Map<string, Array<(event: Event | MessageEvent) => void>>();

	constructor(url: string) {
		this.url = url;
		MockEventSource.instances.push(this);
	}

	addEventListener(type: string, listener: (event: Event | MessageEvent) => void) {
		const handlers = this.listeners.get(type) ?? [];
		handlers.push(listener);
		this.listeners.set(type, handlers);
	}

	close() {
		this.closed = true;
	}

	emit(type: string, payload?: unknown) {
		const handlers = this.listeners.get(type) ?? [];
		const event =
			payload instanceof Event || payload instanceof MessageEvent
				? payload
				: new MessageEvent(type, {
						data: payload === undefined ? '' : JSON.stringify(payload)
					});
		for (const handler of handlers) {
			handler(event);
		}
	}
}

function buildDetail(overrides: Record<string, unknown> = {}) {
	return {
		id: 'gen-123',
		subject: 'Fractions',
		context: 'Explain fractions',
		status: 'running',
		error: null,
		error_type: null,
		error_code: null,
		requested_template_id: 'guided-concept-path',
		resolved_template_id: 'guided-concept-path',
		requested_preset_id: 'blue-classroom',
		resolved_preset_id: 'blue-classroom',
		section_count: 2,
		quality_passed: null,
		generation_time_seconds: null,
		created_at: '2026-03-23T00:00:00Z',
		completed_at: null,
		document_path: 'memory://gen-123',
		planning_spec: {
			id: 'plan-1',
			template_id: 'guided-concept-path',
			preset_id: 'blue-classroom',
			template_decision: {
				chosen_id: 'guided-concept-path',
				chosen_name: 'Guided Concept Path',
				rationale: 'Best fit.',
				fit_score: 0.92,
				alternatives: []
			},
			lesson_rationale: 'Balanced lesson.',
			directives: {
				tone_profile: 'supportive',
				reading_level: 'standard',
				explanation_style: 'balanced',
				example_style: 'everyday',
				scaffold_level: 'medium',
				brevity: 'balanced'
			},
			committed_budgets: {},
			sections: [
				{
					id: 's-01',
					order: 1,
					role: 'intro',
					title: 'What fractions mean',
					objective: 'Frame the idea.',
					focus_note: null,
					selected_components: ['hook-hero'],
					visual_policy: null,
					generation_notes: null,
					rationale: 'Intro first.'
				},
				{
					id: 's-02',
					order: 2,
					role: 'practice',
					title: 'Try the parts',
					objective: 'Apply the concept.',
					focus_note: null,
					selected_components: ['practice-stack'],
					visual_policy: null,
					generation_notes: null,
					rationale: 'Practice second.'
				}
			],
			warning: null,
			source_brief_id: 'brief-1',
			source_brief: {
				intent: 'Teach fractions',
				audience: 'Year 5',
				prior_knowledge: '',
				extra_context: '',
				signals: {
					topic_type: 'concept',
					learning_outcome: 'understand-why',
					class_style: [],
					format: 'printed-booklet'
				},
				preferences: {
					tone: 'supportive',
					reading_level: 'standard',
					explanation_style: 'balanced',
					example_style: 'everyday',
					brevity: 'balanced'
				},
				constraints: {
					more_practice: false,
					keep_short: false,
					use_visuals: false,
					print_first: true
				}
			},
			status: 'committed'
		},
		...overrides
	};
}

function buildDocument(overrides: Record<string, unknown> = {}) {
	return {
		generation_id: 'gen-123',
		subject: 'Fractions',
		context: 'Explain fractions',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		status: 'running',
		section_manifest: [
			{ section_id: 's-01', title: 'What fractions mean', position: 1 },
			{ section_id: 's-02', title: 'Try the parts', position: 2 }
		],
		sections: [
			{
				section_id: 's-01',
				template_id: 'guided-concept-path',
				header: {
					title: 'What fractions mean',
					subject: 'Math',
					grade_band: 'secondary'
				},
				hook: {
					headline: 'Parts of a whole',
					body: 'Fractions tell us how many equal parts we are describing.',
					anchor: 'fractions'
				},
				explanation: {
					body: 'A fraction compares a selected part to the total whole. It can also compare two quantities.',
					emphasis: ['part', 'whole']
				},
				practice: {
					problems: [
						{
							difficulty: 'warm',
							question: 'Shade one half of a square.',
							hints: [{ level: 1, text: 'Split it into two equal parts.' }]
						}
					]
				},
				what_next: {
					body: 'Next we use fractions in examples.',
					next: 'Examples'
				}
			}
		],
		failed_sections: [],
		qc_reports: [],
		quality_passed: null,
		error: null,
		created_at: '2026-03-23T00:00:00Z',
		updated_at: '2026-03-23T00:00:00Z',
		completed_at: null,
		...overrides
	};
}

describe('GenerationView', () => {
	beforeEach(() => {
		MockEventSource.instances = [];
		generationState.set({
			accepted: null,
			document: null,
			connectionBanner: null
		});
		getGenerationDetail.mockReset();
		getGenerationDocument.mockReset();
		buildGenerationEventsUrl.mockClear();
		vi.stubGlobal('EventSource', MockEventSource);
	});

	afterEach(() => {
		cleanup();
		vi.unstubAllGlobals();
	});

	it('renders the live workspace, marks active sections, and shows failed sections inline', async () => {
		getGenerationDetail.mockResolvedValue(buildDetail());
		getGenerationDocument.mockResolvedValue(buildDocument());

		render(GenerationView, {
			props: {
				accepted: {
					generation_id: 'gen-123',
					status: 'running',
					events_url: '/api/v1/generations/gen-123/events',
					document_url: '/api/v1/generations/gen-123/document'
				},
				onReset: vi.fn()
			}
		});

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));
		expect(screen.getByText('Live')).toBeTruthy();
		expect(screen.getByText(/printed booklet/i)).toBeTruthy();
		expect(screen.getByText(/waiting to start/i)).toBeTruthy();

		MockEventSource.instances[0].emit('section_started', {
			type: 'section_started',
			generation_id: 'gen-123',
			section_id: 's-02',
			title: 'Try the parts',
			position: 2
		});

		await waitFor(() => expect(screen.getByText(/writing section content/i)).toBeTruthy());

		MockEventSource.instances[0].emit('section_failed', {
			type: 'section_failed',
			generation_id: 'gen-123',
			section_id: 's-02',
			title: 'Try the parts',
			position: 2,
			failed_at_node: 'writer',
			error_type: 'provider_timeout',
			error_summary: 'Timed out while writing this section.',
			needs_diagram: false,
			needs_worked_example: false,
			attempt_count: 1,
			can_retry: true,
			missing_components: [],
			timestamp: '2026-03-23T00:00:01Z'
		});

		await waitFor(() =>
			expect(screen.getByText(/timed out while writing this section/i)).toBeTruthy()
		);
	});
});
