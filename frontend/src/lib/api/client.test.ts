import { afterEach, describe, expect, it, vi } from 'vitest';

const { authState } = vi.hoisted(() => ({
	authState: {
		token: 'test-token' as string | null
	}
}));

vi.mock('$lib/stores/auth', () => ({
	getToken: () => authState.token,
	authToken: {
		subscribe(run: (value: string | null) => void) {
			run(authState.token);
			return () => {};
		}
	}
}));

import {
	apiFetch,
	buildApiUrl,
	buildGenerationEventsUrl,
	downloadGenerationPdf,
	getGenerationDocument
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

	it('loads v3 booklet documents from the same endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					kind: 'v3_booklet_pack',
					generation_id: 'gen-v3',
					template_id: 'guided-concept-path',
					status: 'final_ready',
					sections: [{ section_id: 's-1', header: { title: 'Intro' } }]
				}),
				{
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				}
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		const payload = await getGenerationDocument('gen-v3');

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/generations/gen-v3/document');
		expect(payload).toMatchObject({
			kind: 'v3_booklet_pack',
			generation_id: 'gen-v3'
		});
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
			new Response('pdf-bytes', {
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
