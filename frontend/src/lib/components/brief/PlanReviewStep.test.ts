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
						rationale: 'Open with a hook.',
						bridges_from: null,
						bridges_to: 'Try the method',
						terms_to_define: ['two-step equation'],
						terms_assumed: [],
						practice_target: 'Check whether the learner can identify the goal of the method.'
					}
				],
				warning: 'Review the scope before generating.',
				source_brief_id: 'brief-1',
				source_brief: {
					subject: 'Math',
					topic: 'Algebra',
					subtopics: ['Solving two-step equations'],
					grade_level: 'grade_7',
					grade_band: 'middle_school',
					class_profile: {
						reading_level: 'below_grade',
						language_support: 'some_ell',
						confidence: 'low',
						prior_knowledge: 'new_topic',
						pacing: 'short_chunks',
						learning_preferences: ['visual', 'step_by_step']
					},
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
		expect(screen.getByText(/pipeline will not add extra components/i)).toBeTruthy();
		expect(screen.getAllByText(/grade 7/i).length).toBeGreaterThan(0);
		expect(screen.getByText(/class profile:/i)).toBeTruthy();
		expect(screen.getByText(/introduces:/i)).toBeTruthy();
		expect(
			screen.getByText((_, element) => element?.textContent === 'Introduces: two-step equation')
		).toBeTruthy();
		expect(screen.getByText(/bridge to:/i)).toBeTruthy();
		expect(screen.getByText(/try the method/i)).toBeTruthy();
		expect(screen.getByText(/practice target:/i)).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /back/i }));
		await fireEvent.click(screen.getByRole('button', { name: /generate/i }));

		expect(onBack).toHaveBeenCalledTimes(1);
		expect(onCommit).toHaveBeenCalledTimes(1);
	});

	it('omits enrichment rows when fields are empty', () => {
		render(PlanReviewStep, {
			plan: {
				id: 'plan-2',
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
				lesson_rationale: 'Keep it compact.',
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
						id: 'section-2',
						order: 1,
						role: 'summary',
						title: 'Check understanding',
						objective: 'Close the resource.',
						focus_note: null,
						selected_components: ['summary-block'],
						visual_policy: null,
						generation_notes: null,
						rationale: 'Close the lesson.',
						bridges_from: null,
						bridges_to: null,
						terms_to_define: [],
						terms_assumed: [],
						practice_target: null
					}
				],
				warning: null,
				source_brief_id: 'brief-2',
				source_brief: {
					subject: 'Math',
					topic: 'Algebra',
					subtopics: ['Solving two-step equations'],
					grade_level: 'grade_7',
					grade_band: 'middle_school',
					class_profile: {
						reading_level: 'below_grade',
						language_support: 'some_ell',
						confidence: 'low',
						prior_knowledge: 'new_topic',
						pacing: 'short_chunks',
						learning_preferences: ['visual']
					},
					learner_context: 'Grade 7 mixed ability',
					intended_outcome: 'practice',
					resource_type: 'worksheet',
					supports: ['worked_examples'],
					depth: 'standard',
					teacher_notes: ''
				},
				status: 'reviewed'
			},
			onBack: vi.fn(),
			onCommit: vi.fn()
		});

		expect(screen.queryByText(/introduces:/i)).toBeNull();
		expect(screen.queryByText(/assumes:/i)).toBeNull();
		expect(screen.queryByText(/bridge from:/i)).toBeNull();
		expect(screen.queryByText(/bridge to:/i)).toBeNull();
		expect(screen.queryByText(/practice target:/i)).toBeNull();
	});
});
