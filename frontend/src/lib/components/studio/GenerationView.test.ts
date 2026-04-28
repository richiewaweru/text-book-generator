// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { generationState } from '$lib/stores/studio';

type EventHandlers = {
	onEvent: (type: string, data: string) => void;
	onError: (err: unknown) => void;
	onOpen?: () => void;
};

const { getGenerationDetail, getGenerationDocument, connectGenerationEvents, capturedHandlers } =
	vi.hoisted(() => {
		let handlers: EventHandlers | null = null;
		return {
			getGenerationDetail: vi.fn(),
			getGenerationDocument: vi.fn(),
			connectGenerationEvents: vi.fn((_id: string, h: EventHandlers) => {
				handlers = h;
				return () => { handlers = null; };
			}),
			capturedHandlers: { get current() { return handlers; } }
		};
	});

vi.mock('$lib/api/client', () => ({
	getGenerationDetail,
	getGenerationDocument,
	connectGenerationEvents
}));

import GenerationView from './GenerationView.svelte';

function emitEvent(type: string, payload?: unknown) {
	const data = payload === undefined ? '' : JSON.stringify(payload);
	capturedHandlers.current?.onEvent(type, data);
}

function buildDetail(overrides: Record<string, unknown> = {}) {
	return {
		id: 'gen-123',
		subject: 'Fractions',
		context: 'Explain fractions',
		mode: 'balanced',
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
					chosen_id: 'worksheet',
					chosen_name: 'Worksheet',
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
				subject: 'Math',
				topic: 'Fractions',
				subtopics: ['Understanding halves and quarters'],
				learner_context: 'Year 5',
				intended_outcome: 'understand',
				resource_type: 'worksheet',
				supports: ['worked_examples'],
				depth: 'standard',
				teacher_notes: ''
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
		mode: 'balanced',
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
		partial_sections: [],
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

function buildPartialSection(overrides: Record<string, unknown> = {}) {
	const section = {
		section_id: 's-02',
		template_id: 'guided-concept-path',
		header: {
			title: 'Try the parts',
			subject: 'Math',
			grade_band: 'secondary'
		},
		hook: {
			headline: 'Split the whole',
			body: 'Fractions divide a whole into equal parts.',
			anchor: 'fractions'
		},
		explanation: {
			body: 'A fraction names how many equal parts we are focusing on.',
			emphasis: ['equal parts']
		},
		practice: {
			problems: [
				{
					difficulty: 'warm',
					question: 'Shade one half of a square.',
					hints: [{ level: 1, text: 'Split the square into two equal parts.' }]
				},
				{
					difficulty: 'medium',
					question: 'Estimate the fraction shown by the shaded region.',
					hints: [{ level: 1, text: 'Count the equal parts.' }]
				}
			]
		},
		what_next: {
			body: 'Next we connect this to equivalent fractions.',
			next: 'Equivalent fractions'
		}
	};
	const { section: sectionOverride, content: _contentOverride, ...rest } = overrides as {
		section?: Record<string, unknown>;
		content?: unknown;
	};
	const nextSection = sectionOverride ?? section;

	return {
		...rest,
		section_id: 's-02',
		template_id: 'guided-concept-path',
		section: nextSection,
		content: nextSection,
		status: 'awaiting_assets',
		visual_mode: 'image',
		pending_assets: ['diagram'],
		updated_at: '2026-03-23T00:00:01Z',
	};
}

describe('GenerationView', () => {
	beforeEach(() => {
		generationState.set({
			accepted: null,
			document: null,
			connectionBanner: null
		});
		getGenerationDetail.mockReset();
		getGenerationDocument.mockReset();
		connectGenerationEvents.mockClear();
	});

	afterEach(() => {
		cleanup();
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
		expect(screen.getByText(/worksheet \/ standard/i)).toBeTruthy();
		expect(screen.getAllByText(/planned/i).length).toBeGreaterThan(0);

		emitEvent('runtime_policy', {
			type: 'runtime_policy',
			generation_id: 'gen-123',
			mode: 'balanced',
			generation_timeout_seconds: 390,
			generation_max_concurrent_per_user: 2,
			max_section_rerenders: 2,
			concurrency: {
				max_section_concurrency: 4,
				max_media_concurrency: 2,
				max_qc_concurrency: 4
			},
			timeouts: {
				curriculum_planner_timeout_seconds: 60,
				content_core_timeout_seconds: 180,
				content_practice_timeout_seconds: 120,
				content_enrichment_timeout_seconds: 90,
				content_repair_timeout_seconds: 120,
				field_regenerator_timeout_seconds: 60,
				qc_timeout_seconds: 60,
				media_inner_timeout_seconds: 45,
				media_node_budget_seconds: 60,
				generation_timeout_base_seconds: 120,
				generation_timeout_per_section_seconds: 90,
				generation_timeout_cap_seconds: 900
			},
			retries: {},
			emitted_at: '2026-03-23T00:00:00Z'
		});
		emitEvent('runtime_progress', {
			type: 'runtime_progress',
			generation_id: 'gen-123',
			snapshot: {
				mode: 'balanced',
				sections_total: 2,
				sections_completed: 1,
				sections_running: 1,
				sections_queued: 0,
				media_running: 1,
				media_queued: 0,
				qc_running: 0,
				qc_queued: 1,
				retry_running: 0,
				retry_queued: 1
			},
			emitted_at: '2026-03-23T00:00:00Z'
		});

		await waitFor(() =>
			expect(screen.getByText(/1 complete \/ 1 running \/ 0 queued/i)).toBeTruthy()
		);
		expect(screen.getByText(/4 sections \/ 2 media \/ 4 qc/i)).toBeTruthy();
		expect(screen.getByText(/390s/i)).toBeTruthy();
		expect(screen.getByText(/render shell/i)).toBeTruthy();
		expect(screen.getByText(/repairs/i)).toBeTruthy();

		emitEvent('section_started', {
			type: 'section_started',
			generation_id: 'gen-123',
			section_id: 's-02',
			title: 'Try the parts',
			position: 2
		});

		await waitFor(() => expect(screen.getAllByText(/^planned$/i).length).toBeGreaterThan(0));

		emitEvent('progress_update', {
			type: 'progress_update',
			generation_id: 'gen-123',
			stage: 'generating_section',
			label: 'Generating section',
			section_id: 's-02'
		});

		await waitFor(() =>
			expect(screen.getAllByText(/generating section/i).length).toBeGreaterThan(0)
		);

		emitEvent('section_failed', {
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

	it('shows media pending copy when the canonical visual mode is image', async () => {
		getGenerationDetail.mockResolvedValue(buildDetail());
		getGenerationDocument.mockResolvedValue(
			buildDocument({
				sections: [],
				partial_sections: [buildPartialSection()]
			})
		);

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

		expect(screen.getAllByText(/generating media/i).length).toBeGreaterThan(0);
		expect(screen.getByText(/Fractions divide a whole into equal parts\./i)).toBeTruthy();
	});

	it('keeps a repair label scoped to the addressed section', async () => {
		getGenerationDetail.mockResolvedValue(buildDetail());
		getGenerationDocument.mockResolvedValue(
			buildDocument({
				sections: [],
				partial_sections: [],
				section_manifest: [
					{ section_id: 's-01', title: 'What fractions mean', position: 1 },
					{ section_id: 's-02', title: 'Try the parts', position: 2 }
				]
			})
		);

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

		emitEvent('progress_update', {
			type: 'progress_update',
			generation_id: 'gen-123',
			stage: 'repairing',
			label: 'Repairing section',
			section_id: 's-01'
		});

		await waitFor(() =>
			expect(screen.getAllByText(/repairing section/i).length).toBeGreaterThan(0)
		);

		const sectionLabels = Array.from(screen.getAllByText(/planned|repairing section/i)).map((node) =>
			node.textContent?.trim()
		);
		expect(sectionLabels.filter((label) => label === 'Repairing section').length).toBeGreaterThan(0);
		expect(sectionLabels.filter((label) => label === 'Planned').length).toBeGreaterThan(0);
	});

	it('updates the partial lesson preview when repeated partial events arrive', async () => {
		getGenerationDetail.mockResolvedValue(buildDetail());
		getGenerationDocument.mockResolvedValue(buildDocument({ sections: [], partial_sections: [] }));

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

		emitEvent('section_partial', {
			type: 'section_partial',
			generation_id: 'gen-123',
			...buildPartialSection()
		});

		await waitFor(() => expect(screen.getByText(/Fractions divide a whole into equal parts\./i)).toBeTruthy());

		emitEvent('section_partial', {
			type: 'section_partial',
			generation_id: 'gen-123',
			...buildPartialSection({
				section: {
					section_id: 's-02',
					template_id: 'guided-concept-path',
					header: {
						title: 'Try the parts, revised',
						subject: 'Math',
						grade_band: 'secondary'
					},
					hook: {
						headline: 'Split the whole',
						body: 'A revised draft now explains equal parts in a new way.',
						anchor: 'fractions'
					},
					explanation: {
						body: 'A fraction names how many equal parts we are focusing on.',
						emphasis: ['equal parts']
					},
					practice: {
						problems: [
							{
								difficulty: 'warm',
								question: 'Shade one half of a square.',
								hints: [{ level: 1, text: 'Split the square into two equal parts.' }]
							},
							{
								difficulty: 'medium',
								question: 'Estimate the fraction shown by the shaded region.',
								hints: [{ level: 1, text: 'Count the equal parts.' }]
							}
						]
					},
					what_next: {
						body: 'Next we connect this to equivalent fractions.',
						next: 'Equivalent fractions'
					}
				},
				updated_at: '2026-03-23T00:00:02Z'
			})
		});

		await waitFor(() =>
			expect(screen.getByText(/revised draft now explains equal parts/i)).toBeTruthy()
		);
	});

	it('marks untouched planned sections as failed after a failed generation', async () => {
		getGenerationDetail.mockResolvedValue(
			buildDetail({
				status: 'failed',
				error: 'The generation failed before the lesson could be completed.',
				error_type: 'pipeline_failed',
				error_code: 'generation_failed',
				quality_passed: false,
				completed_at: '2026-03-23T00:00:01Z'
			})
		);
		getGenerationDocument.mockResolvedValue(
			buildDocument({
				status: 'failed',
				sections: [],
				failed_sections: [
					{
						section_id: 's-01',
						title: 'What fractions mean',
						position: 1,
						focus: null,
						bridges_from: null,
						bridges_to: null,
						needs_diagram: false,
						needs_worked_example: false,
						failed_at_node: 'content_generator',
						error_type: 'validation',
						error_summary: 'This section could not be generated.',
						attempt_count: 1,
						can_retry: true,
						missing_components: ['section-header'],
						failure_detail: null
					}
				],
				partial_sections: []
			})
		);

		render(GenerationView, {
			props: {
				accepted: {
					generation_id: 'gen-123',
					status: 'failed',
					events_url: '/api/v1/generations/gen-123/events',
					document_url: '/api/v1/generations/gen-123/document'
				},
				onReset: vi.fn()
			}
		});

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));

		expect(screen.getAllByText('Failed').length).toBeGreaterThan(0);
		expect(screen.getAllByText(/this section could not be generated/i).length).toBeGreaterThan(0);
	});
});
