import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/stores/auth', () => ({
	getToken: () => 'test-token'
}));

import { apiFetch, buildApiUrl, fetchTextbookHtml } from './client';

describe('client API helpers', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('builds a relative URL when no public API base is configured', () => {
		expect(buildApiUrl('/api/v1/health')).toBe('/api/v1/health');
	});

	it('fetches textbook HTML through the generation-owned endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response('<html></html>', {
				status: 200,
				headers: { 'Content-Type': 'text/html' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);

		await fetchTextbookHtml('gen-123');

		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/generations/gen-123/textbook');
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
});
