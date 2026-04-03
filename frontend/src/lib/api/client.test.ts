import { afterEach, describe, expect, it, vi } from 'vitest';

const { authState } = vi.hoisted(() => ({
	authState: {
		token: 'test-token' as string | null
	}
}));

vi.mock('$lib/stores/auth', () => ({
	getToken: () => authState.token
}));

import {
	apiFetch,
	buildApiUrl,
	buildGenerationEventsUrl,
	downloadGenerationPdf,
	getGenerationDocument,
	planBrief,
	startGeneration
} from './client';

describe('client API helpers', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
		authState.token = 'test-token';
	});

	it('builds a relative URL when no public API base is configured', () => {
		expect(buildApiUrl('/api/v1/health')).toBe('/api/v1/health');
	});

	it('injects the auth token into API fetch calls', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response('{}', {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);

		await apiFetch('/api/v1/profile');

		const init = fetchMock.mock.calls[0][1] as RequestInit;
		const headers = new Headers(init.headers);
		expect(headers.get('Authorization')).toBe('Bearer test-token');
	});

	it('submits template and preset ids with generation requests', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					generation_id: 'gen-123',
					status: 'pending',
					events_url: '/api/v1/generations/gen-123/events',
					document_url: '/api/v1/generations/gen-123/document'
				}),
				{
					status: 202,
					headers: { 'Content-Type': 'application/json' }
				}
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await startGeneration({
			subject: 'calculus',
			context: 'integration practice',
			mode: 'strict',
			template_id: 'guided-concept-path',
			preset_id: 'blue-classroom',
			section_count: 4,
			generation_spec: {
				template_id: 'guided-concept-path',
				preset_id: 'blue-classroom',
				mode: 'strict',
				section_count: 4,
				sections: [],
				warning: null,
				rationale: 'Reviewed plan',
				source_brief: {
					intent: 'Teach derivatives',
					audience: 'Year 10 mixed ability',
					mode: 'strict',
					extra_context: 'Use concrete examples.'
				}
			}
		});

		const init = fetchMock.mock.calls[0][1] as RequestInit;
		expect(init.body).toContain('"template_id":"guided-concept-path"');
		expect(init.body).toContain('"preset_id":"blue-classroom"');
		expect(init.body).toContain('"mode":"strict"');
		expect(init.body).toContain('"generation_spec"');
	});

	it('submits a structured brief planning request', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					template_id: 'guided-concept-path',
					preset_id: 'blue-classroom',
					mode: 'balanced',
					section_count: 3,
					sections: [
						{
							section_id: 's-01',
							position: 1,
							title: 'Start with the problem',
							focus: 'Frame the concept in a concrete situation.',
							role: null,
							required_components: [],
							optional_components: [],
							interaction_policy: null,
							diagram_policy: null,
							enrichment_enabled: false,
							continuity_notes: null
						}
					],
					warning: null,
					rationale: 'This template balances structure and flexibility for first exposure.',
					source_brief: {
						intent: 'Teach derivatives',
						audience: 'Year 10 mixed ability',
						mode: 'balanced',
						extra_context: 'Use concrete examples.'
					}
				}),
				{
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				}
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await planBrief({
			intent: 'Teach derivatives',
			audience: 'Year 10 mixed ability',
			mode: 'balanced',
			extra_context: 'Use concrete examples.'
		});

		const init = fetchMock.mock.calls[0][1] as RequestInit;
		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/brief');
		expect(init.body).toContain('"intent":"Teach derivatives"');
		expect(init.body).toContain('"audience":"Year 10 mixed ability"');
		expect(init.body).toContain('"mode":"balanced"');
		expect(init.body).toContain('"extra_context":"Use concrete examples."');
	});

	it('loads the structured document endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
					JSON.stringify({
						generation_id: 'gen-123',
						subject: 'Calculus',
						context: 'Limits',
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
					created_at: new Date().toISOString(),
					updated_at: new Date().toISOString(),
					completed_at: null
				}),
				{
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				}
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await getGenerationDocument('gen-123');

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/generations/gen-123/document');
	});

	it('builds an EventSource URL without a token query string', () => {
		expect(buildGenerationEventsUrl('gen-123')).toBe('/api/v1/generations/gen-123/events');
	});

	it('falls back to the query token when the auth store is empty', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response('{}', {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);
		authState.token = null;
		vi.stubGlobal('window', {
			location: {
				href: 'http://localhost/textbook/gen-123?print=true&token=query-token'
			}
		} as Window & typeof globalThis);
		await apiFetch('/api/v1/profile');

		const init = fetchMock.mock.calls.at(-1)?.[1] as RequestInit;
		const headers = new Headers(init.headers);
		expect(headers.get('Authorization')).toBe('Bearer query-token');
	});

	it('downloads the exported PDF and returns response metadata', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(new Blob(['pdf-bytes'], { type: 'application/pdf' }), {
				status: 200,
				headers: {
					'Content-Type': 'application/pdf',
					'Content-Disposition': 'attachment; filename="lesson.pdf"',
					'X-Page-Count': '12'
				}
			})
		);
		const clickMock = vi.fn();
		const createObjectUrl = vi.fn(() => 'blob:download');
		const revokeObjectUrl = vi.fn();
		const createElement = vi.fn(() => ({ click: clickMock, href: '', download: '' }));

		vi.stubGlobal('fetch', fetchMock);
		vi.stubGlobal('URL', {
			createObjectURL: createObjectUrl,
			revokeObjectURL: revokeObjectUrl
		});
		vi.stubGlobal('document', {
			createElement
		} as unknown as Document);

		const result = await downloadGenerationPdf('gen-123', {
			school_name: 'Springfield High',
			teacher_name: 'Ms. Johnson',
			include_toc: true,
			include_answers: false
		});

		expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/generations/gen-123/export/pdf');
		expect(clickMock).toHaveBeenCalledTimes(1);
		expect(result).toEqual({ filename: 'lesson.pdf', pageCount: '12' });
		expect(createObjectUrl).toHaveBeenCalledTimes(1);
		expect(revokeObjectUrl).toHaveBeenCalledWith('blob:download');
	});
});
