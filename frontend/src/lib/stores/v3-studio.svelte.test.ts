import { describe, expect, it } from 'vitest';

import { resetV3Studio, v3Studio } from './v3-studio.svelte';

describe('v3Studio architect mode', () => {
	it('defaults to chunked and resets back to chunked', () => {
		expect(v3Studio.architectMode).toBe('chunked');

		v3Studio.architectMode = 'standard';
		expect(v3Studio.architectMode).toBe('standard');

		resetV3Studio();
		expect(v3Studio.architectMode).toBe('chunked');
	});
});

