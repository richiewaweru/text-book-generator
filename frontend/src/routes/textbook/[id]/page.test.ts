// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type EventHandlers = {
	onEvent: (type: string, data: string) => void;
	onError: (err: unknown) => void;
	onOpen?: () => void;
};

const {
	pageState,
	getGenerationDetail,
	getGenerationDocument,
	connectGenerationEvents,
	downloadGenerationPdf,
	capturedHandlers
} = vi.hoisted(() => {
	let handlers: EventHandlers | null = null;
	return {
		pageState: {
			params: { id: 'gen-123' },
			url: new URL('http://localhost/textbook/gen-123')
		},
		getGenerationDetail: vi.fn(),
		getGenerationDocument: vi.fn(),
		connectGenerationEvents: vi.fn((_id: string, h: EventHandlers) => {
			handlers = h;
			return () => { handlers = null; };
		}),
		downloadGenerationPdf: vi.fn(),
		capturedHandlers: { get current() { return handlers; } }
	};
});

vi.mock('$app/state', () => ({
	page: pageState
}));

vi.mock('lectio', () => ({
	providePrintMode: vi.fn()
}));

vi.mock('$lib/components/PrintSectionLink.svelte', async () => ({
	default: (await import('./__fixtures__/MockPrintSectionLink.svelte')).default
}));

vi.mock('$lib/api/client', () => ({
	getGenerationDetail,
	getGenerationDocument,
	connectGenerationEvents,
	downloadGenerationPdf
}));

vi.mock('$lib/components/LectioDocumentView.svelte', async () => ({
	default: (await import('./__fixtures__/MockLectioDocumentView.svelte')).default
}));

import TextbookPage from './+page.svelte';

function emitEvent(type: string, payload?: unknown) {
	const data = payload === undefined ? '' : JSON.stringify(payload);
	capturedHandlers.current?.onEvent(type, data);
}

function emitError(err?: unknown) {
	capturedHandlers.current?.onError(err ?? new Error('stream error'));
}

function buildDetail(overrides: Record<string, unknown> = {}) {
		return {
			id: 'gen-123',
			subject: 'Algebra',
			context: 'Explain algebra',
			status: 'running',
			error: null,
		error_type: null,
		error_code: null,
		requested_template_id: 'guided-concept-path',
		resolved_template_id: 'guided-concept-path',
		requested_preset_id: 'blue-classroom',
		resolved_preset_id: 'blue-classroom',
		section_count: 4,
		quality_passed: null,
		generation_time_seconds: null,
		created_at: '2026-03-23T00:00:00Z',
		completed_at: null,
		document_path: 'memory://gen-123',
		report_url: '/api/v1/generations/gen-123/report',
		planning_spec: null,
		...overrides
	};
}

function buildDocument(overrides: Record<string, unknown> = {}) {
		return {
			generation_id: 'gen-123',
			subject: 'Algebra',
			context: 'Explain algebra',
			template_id: 'guided-concept-path',
			preset_id: 'blue-classroom',
			status: 'running',
		section_manifest: [
			{ section_id: 's-01', title: 'Section 1', position: 1 },
			{ section_id: 's-02', title: 'Section 2', position: 2 },
			{ section_id: 's-03', title: 'Section 3', position: 3 },
			{ section_id: 's-04', title: 'Section 4', position: 4 }
		],
		sections: [],
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

describe('textbook page stream lifecycle', () => {
	beforeEach(() => {
		getGenerationDetail.mockReset();
		getGenerationDocument.mockReset();
		connectGenerationEvents.mockClear();
		downloadGenerationPdf.mockReset();
		pageState.url = new URL('http://localhost/textbook/gen-123');
	});

	afterEach(() => {
		cleanup();
	});

	it('opens one stream and performs one terminal refresh on complete', async () => {
		getGenerationDetail
			.mockResolvedValueOnce(buildDetail())
			.mockResolvedValueOnce(
				buildDetail({
					status: 'completed',
					quality_passed: false,
					completed_at: '2026-03-23T00:01:00Z'
				})
			);
		getGenerationDocument
			.mockResolvedValueOnce(buildDocument())
			.mockResolvedValueOnce(
				buildDocument({
					status: 'completed',
					sections: [
						{
							section_id: 's-01',
							header: { title: 'Section 1' }
						}
					],
					qc_reports: [
						{ section_id: 's-01', passed: true, issues: [], warnings: [] },
						{ section_id: 's-02', passed: true, issues: [], warnings: [] },
						{ section_id: 's-03', passed: true, issues: [], warnings: [] },
						{
							section_id: 's-04',
							passed: false,
							issues: [{ block: 'practice', severity: 'blocking', message: 'Needs retry' }],
							warnings: []
						}
					],
					quality_passed: false,
					completed_at: '2026-03-23T00:01:00Z'
				})
			);

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));
		expect(connectGenerationEvents).toHaveBeenCalledTimes(1);

		emitEvent('complete', { type: 'complete', generation_id: 'gen-123' });

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(2));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(2));

		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(getGenerationDetail).toHaveBeenCalledTimes(2);
		expect(getGenerationDocument).toHaveBeenCalledTimes(2);
		expect(screen.getByText(/Stream: completed with QC issues/i)).toBeTruthy();
		expect(screen.getByText(/QC: 3 \/ 4 passing/i)).toBeTruthy();
	});

	it('shows completed with QC issues without reopening the stream', async () => {
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'completed',
				quality_passed: false,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);
		getGenerationDocument.mockResolvedValueOnce(
			buildDocument({
				status: 'completed',
				qc_reports: [
					{ section_id: 's-01', passed: true, issues: [], warnings: [] },
					{ section_id: 's-02', passed: false, issues: [], warnings: [] }
				],
				quality_passed: false,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		expect(connectGenerationEvents).not.toHaveBeenCalled();
		expect(screen.getByText(/Stream: completed with QC issues/i)).toBeTruthy();
	});

	it('performs one guarded refresh on generic stream errors without opening a new stream', async () => {
		getGenerationDetail
			.mockResolvedValueOnce(buildDetail())
			.mockResolvedValueOnce(
				buildDetail({
					status: 'failed',
					error: 'Generation timed out after 300 seconds.',
					error_type: 'runtime_error',
					error_code: 'generation_timeout',
					quality_passed: false,
					completed_at: '2026-03-23T00:01:00Z'
				})
			);
		getGenerationDocument
			.mockResolvedValueOnce(buildDocument())
			.mockResolvedValueOnce(
				buildDocument({
					status: 'failed',
					quality_passed: false,
					error: 'Generation timed out after 300 seconds.',
					completed_at: '2026-03-23T00:01:00Z'
				})
			);

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));
		expect(connectGenerationEvents).toHaveBeenCalledTimes(1);

		emitError();

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(2));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(2));

		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(getGenerationDetail).toHaveBeenCalledTimes(2);
		expect(getGenerationDocument).toHaveBeenCalledTimes(2);
		expect(screen.getByText(/Generation timed out after 300 seconds\./i)).toBeTruthy();
	});

	it('shows failed sections as soon as section_failed arrives on the stream', async () => {
		getGenerationDetail.mockResolvedValueOnce(buildDetail());
		getGenerationDocument.mockResolvedValueOnce(buildDocument());

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));
		expect(connectGenerationEvents).toHaveBeenCalledTimes(1);

		emitEvent('section_failed', {
			type: 'section_failed',
			generation_id: 'gen-123',
			section_id: 's-03',
			title: 'Section 3',
			position: 3,
			failed_at_node: 'content_generator',
			error_type: 'validation',
			error_summary: 'Schema validation failed after one repair attempt.',
			needs_diagram: false,
			needs_worked_example: false,
			attempt_count: 1,
			can_retry: true,
			missing_components: ['section-header', 'hook-hero']
		});

		await waitFor(() => expect(screen.getByText(/Failed sections: 1/i)).toBeTruthy());
		expect(screen.getByText(/Sections Not Completed/i)).toBeTruthy();
		expect(
			screen.getByText(/Failed at content_generator: Schema validation failed after one repair attempt\./i)
		).toBeTruthy();
	});

	it('shows progress updates from the stream and keeps section panels informational', async () => {
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'running',
				quality_passed: null
			})
		);
		getGenerationDocument.mockResolvedValueOnce(buildDocument());

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));
		expect(connectGenerationEvents).toHaveBeenCalledTimes(1);

		emitEvent('runtime_policy', {
			type: 'runtime_policy',
			generation_id: 'gen-123',
			mode: 'balanced',
			generation_timeout_seconds: 390,
			generation_max_concurrent_per_user: 2,
			max_section_rerenders: 2,
			concurrency: {
				max_section_concurrency: 4,
				max_diagram_concurrency: 2,
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
				diagram_inner_timeout_seconds: 45,
				diagram_node_budget_seconds: 60,
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
				sections_total: 4,
				sections_completed: 1,
				sections_running: 1,
				sections_queued: 2,
				diagram_running: 1,
				diagram_queued: 0,
				qc_running: 0,
				qc_queued: 1,
				retry_running: 0,
				retry_queued: 1
			},
			emitted_at: '2026-03-23T00:00:00Z'
		});
		emitEvent('progress_update', {
			type: 'progress_update',
			generation_id: 'gen-123',
			stage: 'planning',
			label: 'Planning lesson structure'
		});

		await waitFor(() => expect(screen.getByText(/Progress: Planning lesson structure/i)).toBeTruthy());
		expect(screen.getByText(/Stage: planning/i)).toBeTruthy();
		expect(screen.getByText(/Runtime sections: 1 complete \/ 1 running \/ 2 queued/i)).toBeTruthy();
		expect(screen.getByText(/Policy: 4 section \/ 2 diagram \/ 4 QC workers/i)).toBeTruthy();
		expect(screen.getByText(/Budget: 390s total, rerenders 2 max/i)).toBeTruthy();
	});

	it('renders failed and weak sections without enhancement actions', async () => {
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'completed',
				quality_passed: false,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);
		getGenerationDocument.mockResolvedValueOnce(
			buildDocument({
				status: 'completed',
				failed_sections: [
					{
						section_id: 's-01',
						title: 'Section 1',
						position: 1,
						focus: 'Focus one',
						bridges_from: null,
						bridges_to: null,
						needs_diagram: false,
						needs_worked_example: false,
						failed_at_node: 'content_generator',
						error_type: 'validation',
						error_summary: 'Missing practice',
						attempt_count: 1,
						can_retry: true,
						missing_components: ['practice'],
						failure_detail: null
					}
				],
				qc_reports: [
					{
						section_id: 's-02',
						passed: false,
						issues: [{ block: 'diagram', severity: 'blocking', message: 'Need diagram' }],
						warnings: ['Needs a diagram']
					}
				],
				sections: [{ section_id: 's-02', header: { title: 'Section 2' } }],
				section_manifest: [
					{ section_id: 's-01', title: 'Section 1', position: 1 },
					{ section_id: 's-02', title: 'Section 2', position: 2 }
				],
				quality_passed: false,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);

		render(TextbookPage);

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(1));

		expect(screen.getByText(/Sections Not Completed/i)).toBeTruthy();
		expect(screen.getByText(/Section 1/i)).toBeTruthy();
		expect(screen.getByText(/Failed at content_generator: Missing practice/i)).toBeTruthy();
		expect(screen.getByText(/Sections Needing Another Pass/i)).toBeTruthy();
		expect(screen.getByText(/Section 2/i)).toBeTruthy();
		expect(screen.getByText(/Needs a diagram/i)).toBeTruthy();
		expect(screen.queryByRole('button', { name: /improve section/i })).toBeNull();
		expect(screen.queryByRole('button', { name: /retry diagram/i })).toBeNull();
	});

	it('shows the export pdf action for completed generations', async () => {
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'completed',
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);
		getGenerationDocument.mockResolvedValueOnce(
			buildDocument({
				status: 'completed',
				sections: [
					{
						section_id: 's-01',
						header: { title: 'Section 1' }
					}
				],
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);

		render(TextbookPage);

		await waitFor(() => expect(screen.getByRole('button', { name: /export pdf/i })).toBeTruthy());
		expect(connectGenerationEvents).not.toHaveBeenCalled();
	});

	it('marks the print route complete when a completed document is fully ready', async () => {
		pageState.url = new URL('http://localhost/textbook/gen-123?print=true&token=abc');
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'completed',
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);
		getGenerationDocument.mockResolvedValueOnce(
			buildDocument({
				status: 'completed',
				sections: [
					{
						section_id: 's-01',
						header: { title: 'Section 1' }
					},
					{
						section_id: 's-02',
						header: { title: 'Section 2' }
					},
					{
						section_id: 's-03',
						header: { title: 'Section 3' }
					},
					{
						section_id: 's-04',
						header: { title: 'Section 4' }
					}
				],
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);

		const { container } = render(TextbookPage);
		await waitFor(() =>
			expect(container.querySelector('[data-generation-complete="true"]')).toBeTruthy()
		);
		expect(screen.queryByRole('button', { name: /export pdf/i })).toBeNull();
		expect(connectGenerationEvents).not.toHaveBeenCalled();
	});

	it('shows teacher and student export presets for completed generations', async () => {
		getGenerationDetail.mockResolvedValueOnce(
			buildDetail({
				status: 'completed',
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);
		getGenerationDocument.mockResolvedValueOnce(
			buildDocument({
				status: 'completed',
				sections: [{ section_id: 's-01', header: { title: 'Section 1' } }],
				quality_passed: true,
				completed_at: '2026-03-23T00:01:00Z'
			})
		);

		render(TextbookPage);
		await waitFor(() => expect(screen.getByRole('button', { name: /export pdf/i })).toBeTruthy());
		screen.getByRole('button', { name: /export pdf/i }).click();

		await waitFor(() => expect(screen.getByRole('button', { name: /teacher copy/i })).toBeTruthy());
		expect(screen.getByRole('button', { name: /student copy/i })).toBeTruthy();
	});
});
