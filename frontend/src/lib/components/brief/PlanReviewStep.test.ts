// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import PlanReviewStep from './PlanReviewStep.svelte';

describe('PlanReviewStep', () => {
	it('renders rationale, warning, sections, and fires actions', async () => {
		const onBack = vi.fn();
		const onCommit = vi.fn();

		render(PlanReviewStep, {
			plan: {
				id: 'plan-1',
				template_id: 'guided-concept-path',
				preset_id: 'blue-classroom',
				mode: 'balanced',
				template_decision: {
					chosen_id: 'worksheet',
					chosen_name: 'Worksheet',
					rationale: 'Teacher selected Worksheet.',
					fit_score: 1,
					alternatives: []
				},
				lesson_rationale: 'Move from setup into guided practice.',
				directives: {
					tone_profile: 'supportive',
					reading_level: 'standard',
					explanation_style: 'balanced',
					example_style: 'everyday',
					scaffold_level: 'medium',
					brevity: 'balanced'
				},
				committed_budgets: {},
				sections: [
					{
						id: 'section-1',
						order: 1,
						role: 'intro',
						title: 'Start with the idea',
						objective: 'Open the resource clearly.',
						focus_note: null,
						selected_components: ['hook-hero', 'explanation-block'],
						visual_policy: null,
						generation_notes: null,
						rationale: 'Open with a hook.'
					}
				],
				warning: 'Review the scope before generating.',
				source_brief_id: 'brief-1',
				source_brief: {
					subject: 'Math',
					topic: 'Algebra',
					subtopic: 'Solving two-step equations',
					learner_context: 'Grade 7 mixed ability',
					intended_outcome: 'practice',
					resource_type: 'worksheet',
					supports: ['worked_examples'],
					depth: 'standard',
					teacher_notes: ''
				},
				status: 'reviewed'
			},
			onBack,
			onCommit
		});

		expect(screen.getByText(/move from setup into guided practice/i)).toBeTruthy();
		expect(screen.getByText(/review the scope before generating/i)).toBeTruthy();
		expect(screen.getByText(/start with the idea/i)).toBeTruthy();
		expect(screen.getByText(/hook/i)).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /back/i }));
		await fireEvent.click(screen.getByRole('button', { name: /generate/i }));

		expect(onBack).toHaveBeenCalledTimes(1);
		expect(onCommit).toHaveBeenCalledTimes(1);
	});
});
