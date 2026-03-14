import { describe, expect, it } from 'vitest';

import type { GenerationStatus } from '$lib/types';

import { hasRetryContext, progressPercent, resolveGenerationMode } from './progress';

describe('generation progress helpers', () => {
	it('resolves the active mode from progress or result payloads', () => {
		const running: GenerationStatus = {
			id: 'gen-1',
			status: 'running',
			mode: null,
			progress: {
				mode: 'draft',
				phase: 'generating',
				message: 'Writing section 1 of 8...',
				sections_total: 8,
				sections_completed: 1,
				current_section_id: 'section_01',
				current_section_title: 'Intro',
				retry_attempt: null,
				retry_limit: null,
				flagged_section_ids: []
			},
			result: null,
			error: null,
			error_type: null,
			source_generation_id: null
		};
		const completed: GenerationStatus = {
			...running,
			status: 'completed',
			progress: null,
			result: {
				textbook_id: 'tb-1',
				mode: 'balanced',
				quality_report: null,
				generation_time_seconds: 12,
				quality_reruns: 0,
				source_generation_id: 'draft-1'
			}
		};

		expect(resolveGenerationMode(running)).toBe('draft');
		expect(resolveGenerationMode(completed)).toBe('balanced');
	});

	it('computes progress percentages from section counts', () => {
		expect(
			progressPercent({
				mode: 'balanced',
				phase: 'checking',
				message: 'Checking...',
				sections_total: 12,
				sections_completed: 6,
				current_section_id: null,
				current_section_title: null,
				retry_attempt: null,
				retry_limit: null,
				flagged_section_ids: []
			})
		).toBe(50);
		expect(progressPercent(null)).toBe(0);
	});

	it('detects retry context only when both attempt and limit are present', () => {
		expect(
			hasRetryContext({
				mode: 'balanced',
				phase: 'fixing',
				message: 'Fixing...',
				sections_total: 10,
				sections_completed: 10,
				current_section_id: 'section_04',
				current_section_title: 'Series',
				retry_attempt: 1,
				retry_limit: 3,
				flagged_section_ids: ['section_04']
			})
		).toBe(true);
		expect(
			hasRetryContext({
				mode: 'draft',
				phase: 'generating',
				message: 'Writing...',
				sections_total: 10,
				sections_completed: 1,
				current_section_id: null,
				current_section_title: null,
				retry_attempt: null,
				retry_limit: 3,
				flagged_section_ids: []
			})
		).toBe(false);
	});
});
