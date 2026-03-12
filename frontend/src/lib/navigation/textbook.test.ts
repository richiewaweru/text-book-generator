import { describe, expect, it } from 'vitest';

import { getTextbookRoute } from './textbook';

describe('textbook navigation helpers', () => {
	it('builds textbook viewer routes from generation ids', () => {
		expect(getTextbookRoute('gen-123')).toBe('/textbook/gen-123');
	});
});
