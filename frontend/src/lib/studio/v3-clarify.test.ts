import { describe, expect, it } from 'vitest';

import { hasRequiredStructuredFields } from '$lib/studio/v3-clarify';
import type { V3InputForm } from '$lib/types/v3';

function makeForm(overrides: Partial<V3InputForm> = {}): V3InputForm {
	return {
		grade_level: 'Grade 7',
		subject: 'Mathematics',
		duration_minutes: 50,
		topic: 'Compound area',
		subtopics: ['L-shapes'],
		prior_knowledge: 'Rectangle area',
		lesson_mode: 'first_exposure',
		lesson_mode_other: '',
		intended_outcome: 'understand',
		intended_outcome_other: '',
		learner_level: 'on_grade',
		reading_level: 'on_grade',
		language_support: 'none',
		prior_knowledge_level: 'some_background',
		support_needs: [],
		learning_preferences: [],
		free_text: '',
		...overrides
	};
}

describe('hasRequiredStructuredFields', () => {
	it('returns true for complete structured form', () => {
		expect(hasRequiredStructuredFields(makeForm())).toBe(true);
	});

	it('returns false when topic is too short', () => {
		expect(hasRequiredStructuredFields(makeForm({ topic: 'ab' }))).toBe(false);
	});

	it('returns false when required fields are empty', () => {
		expect(hasRequiredStructuredFields(makeForm({ grade_level: '' }))).toBe(false);
		expect(hasRequiredStructuredFields(makeForm({ subject: '' }))).toBe(false);
	});
});

