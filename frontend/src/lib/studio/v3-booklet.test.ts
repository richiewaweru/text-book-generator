import { describe, expect, it } from 'vitest';

import { getBookletExportPolicy, isBookletStatus } from './v3-booklet';

describe('isBookletStatus', () => {
	it('accepts valid statuses and rejects unknown values', () => {
		expect(isBookletStatus('draft_ready')).toBe(true);
		expect(isBookletStatus('final_with_warnings')).toBe(true);
		expect(isBookletStatus('unknown')).toBe(false);
		expect(isBookletStatus(null)).toBe(false);
	});
});

describe('getBookletExportPolicy', () => {
	it('enables final exports', () => {
		expect(getBookletExportPolicy('final_ready')).toMatchObject({
			enabled: true,
			requiresConfirm: false
		});
	});

	it('requires confirmation for review-needed drafts', () => {
		expect(getBookletExportPolicy('draft_needs_review')).toMatchObject({
			enabled: true,
			requiresConfirm: true
		});
	});

	it('disables unusable drafts', () => {
		expect(getBookletExportPolicy('failed_unusable')).toMatchObject({
			enabled: false
		});
	});
});
