import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/stores/auth', () => ({
	getToken: () => 'test-token'
}));

import {
	apiFetch,
	buildApiUrl,
	buildGenerationEventsUrl,
	getGenerationDocument,
	startGeneration
} from './client';

describe('client API helpers', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
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
					mode: 'balanced',
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
			mode: 'balanced',
			template_id: 'guided-concept-path',
			preset_id: 'blue-classroom',
			section_count: 4
		});

		const init = fetchMock.mock.calls[0][1] as RequestInit;
		expect(init.body).toContain('"template_id":"guided-concept-path"');
		expect(init.body).toContain('"preset_id":"blue-classroom"');
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
					source_generation_id: null,
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

	it('builds an EventSource URL with the token query string', () => {
		expect(buildGenerationEventsUrl('gen-123')).toBe(
			'/api/v1/generations/gen-123/events?token=test-token'
		);
	});
});
