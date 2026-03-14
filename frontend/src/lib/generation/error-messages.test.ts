import { describe, expect, it } from 'vitest';

import { friendlyGenerationErrorMessage } from './error-messages';

describe('friendlyGenerationErrorMessage', () => {
	it('preserves actionable provider errors', () => {
		expect(
			friendlyGenerationErrorMessage(
				"Provider 'claude' request failed: Anthropic reports that the API credit balance is too low.",
				'provider_error'
			)
		).toContain('credit balance');
	});

	it('keeps generic pipeline errors generic', () => {
		expect(
			friendlyGenerationErrorMessage(
				"Pipeline node 'CurriculumPlannerNode' failed",
				'pipeline_error'
			)
		).toBe('The generation pipeline encountered an error. Please try again with different input.');
	});
});
