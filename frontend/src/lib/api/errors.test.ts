import { describe, expect, it } from 'vitest';

import { ApiError, ensureOk } from './errors';

describe('ensureOk', () => {
	it('uses a friendly concurrency message for 429 responses', async () => {
		const response = new Response('', {
			status: 429,
			statusText: 'Too Many Requests'
		});

		const error = await ensureOk(response, 'Generation failed.').catch((value) => value);

		expect(error).toBeInstanceOf(ApiError);
		expect((error as ApiError).detail).toContain('maximum number of active generations');
	});
});
