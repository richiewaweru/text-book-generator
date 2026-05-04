import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import V3PlanningState from './V3PlanningState.svelte';

describe('V3PlanningState', () => {
	it('renders teacher inputs when form is present', () => {
		render(V3PlanningState, {
			props: {
				form: {
					grade_level: 'Grade 7',
					subject: 'Mathematics',
					duration_minutes: 50,
					topic: 'Compound area',
					subtopics: ['L-shapes'],
					prior_knowledge: '',
					lesson_mode: 'first_exposure',
					lesson_mode_other: '',
					intended_outcome: 'understand',
					intended_outcome_other: '',
					learner_level: 'on_grade',
					reading_level: 'on_grade',
					language_support: 'some_ell',
					prior_knowledge_level: 'new_topic',
					support_needs: ['visuals'],
					learning_preferences: ['step_by_step'],
					free_text: ''
				}
			}
		});

		expect(screen.getByText('Grade')).toBeTruthy();
		expect(screen.getByText('Grade 7')).toBeTruthy();
		expect(screen.getByText('Compound area')).toBeTruthy();
		expect(screen.getByText(/Subtopics:/)).toBeTruthy();
	});
});

