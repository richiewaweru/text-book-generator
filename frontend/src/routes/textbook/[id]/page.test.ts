// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const {
	goto,
	pageState,
	getGenerationDetail,
	getGenerationDocument,
	buildGenerationEventsUrl,
	enhanceGeneration
} = vi.hoisted(() => ({
	goto: vi.fn(),
	pageState: { params: { id: 'gen-123' } },
	getGenerationDetail: vi.fn(),
	getGenerationDocument: vi.fn(),
	buildGenerationEventsUrl: vi.fn((id: string) => `/api/v1/generations/${id}/events`),
	enhanceGeneration: vi.fn()
}));

vi.mock('$app/navigation', () => ({
	goto
}));

vi.mock('$app/state', () => ({
	page: pageState
}));

vi.mock('$lib/api/client', () => ({
	getGenerationDetail,
	getGenerationDocument,
	buildGenerationEventsUrl,
	enhanceGeneration
}));

vi.mock('$lib/components/LectioDocumentView.svelte', async () => ({
	default: (await import('./__fixtures__/MockLectioDocumentView.svelte')).default
}));

import TextbookPage from './+page.svelte';

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
		subject: 'Algebra',
		context: 'Explain algebra',
		status: 'running',
		mode: 'draft',
		source_generation_id: null,
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
		...overrides
	};
}

function buildDocument(overrides: Record<string, unknown> = {}) {
	return {
		generation_id: 'gen-123',
		subject: 'Algebra',
		context: 'Explain algebra',
		mode: 'draft',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		source_generation_id: null,
		status: 'running',
		section_manifest: [
			{ section_id: 's-01', title: 'Section 1', position: 1 },
			{ section_id: 's-02', title: 'Section 2', position: 2 },
			{ section_id: 's-03', title: 'Section 3', position: 3 },
			{ section_id: 's-04', title: 'Section 4', position: 4 }
		],
		sections: [],
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
		MockEventSource.instances = [];
		goto.mockReset();
		getGenerationDetail.mockReset();
		getGenerationDocument.mockReset();
		buildGenerationEventsUrl.mockClear();
		enhanceGeneration.mockReset();
		vi.stubGlobal('EventSource', MockEventSource);
	});

	afterEach(() => {
		cleanup();
		vi.unstubAllGlobals();
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
		expect(MockEventSource.instances).toHaveLength(1);

		MockEventSource.instances[0].emit('complete', { type: 'complete', generation_id: 'gen-123' });

		await waitFor(() => expect(getGenerationDetail).toHaveBeenCalledTimes(2));
		await waitFor(() => expect(getGenerationDocument).toHaveBeenCalledTimes(2));
		expect(MockEventSource.instances).toHaveLength(1);
		expect(MockEventSource.instances[0].closed).toBe(true);

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
		expect(MockEventSource.instances).toHaveLength(0);
		expect(screen.getByText(/Stream: completed with QC issues/i)).toBeTruthy();
	});
});
