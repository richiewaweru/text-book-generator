import { describe, expect, it } from 'vitest';

import { resolveClientApiBase, resolveDevProxyTarget } from './config';

describe('API config resolution', () => {
	it('uses relative client paths when no API base is configured', () => {
		expect(resolveClientApiBase({})).toBe('');
	});

	it('prefers PUBLIC_API_URL for browser API calls', () => {
		expect(
			resolveClientApiBase({
				PUBLIC_API_URL: 'http://localhost:8001/',
				VITE_API_TARGET: 'http://localhost:8000/'
			})
		).toBe('http://localhost:8001');
	});

	it('falls back to VITE_API_TARGET for browser API calls', () => {
		expect(resolveClientApiBase({ VITE_API_TARGET: 'http://localhost:8001/' })).toBe(
			'http://localhost:8001'
		);
	});

	it('prefers VITE_API_TARGET for the dev proxy target', () => {
		expect(
			resolveDevProxyTarget({
				PUBLIC_API_URL: 'http://localhost:8001/',
				VITE_API_TARGET: 'http://localhost:8002/'
			})
		).toBe('http://localhost:8002');
	});

	it('uses PUBLIC_API_URL for the dev proxy when no explicit VITE target is set', () => {
		expect(resolveDevProxyTarget({ PUBLIC_API_URL: 'http://localhost:8001/' })).toBe(
			'http://localhost:8001'
		);
	});
});
