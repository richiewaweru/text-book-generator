// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { commitPlan, planFromBrief, resolveTopic, reviewTeacherBrief, validateTeacherBrief } = vi.hoisted(() => ({
	commitPlan: vi.fn(),
	planFromBrief: vi.fn(),
	resolveTopic: vi.fn(),
	reviewTeacherBrief: vi.fn(),
	validateTeacherBrief: vi.fn()
}));

const { getProfile } = vi.hoisted(() => ({
	getProfile: vi.fn()
}));

vi.mock('$lib/api/teacher-brief', () => ({
	commitPlan,
	planFromBrief,
	resolveTopic,
	reviewTeacherBrief,
	validateTeacherBrief
}));

vi.mock('$lib/api/profile', () => ({
	getProfile
}));

import TeacherBriefBuilder from './TeacherBriefBuilder.svelte';

async function moveIntoClassProfile() {
	await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
		target: { value: 'Algebra' }
	});
	await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));

	await waitFor(() =>
		expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
	);
	await fireEvent.click(screen.getByRole('button', { name: /solving two-step equations/i }));
	await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
	await waitFor(() => expect(screen.getByRole('button', { name: /grade 7/i })).toBeTruthy());
	await fireEvent.click(screen.getByRole('button', { name: /grade 7/i }));
	await waitFor(() => expect(screen.getByLabelText(/reading level/i)).toBeTruthy());
}

async function completeAudienceFlow() {
	await moveIntoClassProfile();
	await fireEvent.change(screen.getByLabelText(/reading level/i), {
		target: { value: 'below_grade' }
	});
	await fireEvent.change(screen.getByLabelText(/language support/i), {
		target: { value: 'some_ell' }
	});
	await fireEvent.change(screen.getByLabelText(/confidence/i), {
		target: { value: 'low' }
	});
	await fireEvent.change(screen.getByLabelText(/prior knowledge/i), {
		target: { value: 'new_topic' }
	});
	await fireEvent.change(screen.getByLabelText(/pacing/i), {
		target: { value: 'short_chunks' }
	});
	await fireEvent.click(screen.getByRole('button', { name: /visual anchors/i }));
	await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
}

describe('TeacherBriefBuilder', () => {
	beforeEach(() => {
		commitPlan.mockReset();
		planFromBrief.mockReset();
		resolveTopic.mockReset();
		reviewTeacherBrief.mockReset();
		validateTeacherBrief.mockReset();
		getProfile.mockResolvedValue({
			id: 'profile-1',
			user_id: 'user-1',
			teacher_role: 'teacher',
			subjects: ['mathematics'],
			default_grade_band: 'middle',
			default_audience_description: 'Grade 7 mixed-ability class',
			curriculum_framework: 'Common Core',
			classroom_context: 'Some learners struggle with word problems',
			planning_goals: 'Faster drafting',
			school_or_org_name: 'Riverside',
			delivery_preferences: {
				tone: 'supportive',
				reading_level: 'standard',
				explanation_style: 'balanced',
				example_style: 'everyday',
				brevity: 'balanced',
				use_visuals: true,
				print_first: false,
				more_practice: false,
				keep_short: false
			},
			created_at: '2026-04-27T00:00:00Z',
			updated_at: '2026-04-27T00:00:00Z'
		});
		resolveTopic.mockResolvedValue({
			subject: 'Math',
			topic: 'Algebra',
			candidate_subtopics: [
				{
					id: 'two-step-equations',
					title: 'Solving two-step equations',
					description: 'Solve equations with two operations.',
					likely_grade_band: 'middle school'
				}
			],
			needs_clarification: false,
			clarification_message: null
		});
	});

	afterEach(() => {
		cleanup();
	});

	it('walks from topic capture to review and surfaces validation feedback', async () => {
		validateTeacherBrief.mockResolvedValue({
			is_ready: false,
			blockers: [{ field: 'subtopics', message: 'Pick narrower subtopics before generation.' }],
			warnings: [{ field: 'supports', message: 'Too many supports may crowd a quick resource.' }],
			suggestions: [{ field: 'subtopics', suggestion: 'Tighten each subtopic to one teachable skill.' }]
		});

		render(TeacherBriefBuilder);

		await completeAudienceFlow();
		await fireEvent.click(screen.getByRole('button', { name: /practice a skill/i }));
		await fireEvent.click(screen.getByRole('button', { name: /worksheet/i }));

		await waitFor(() =>
			expect(screen.getByRole('button', { name: /worked examples/i }).getAttribute('aria-pressed')).toBe(
				'true'
			)
		);
		expect(screen.getByRole('button', { name: /step-by-step hints/i }).getAttribute('aria-pressed')).toBe(
			'true'
		);
		expect(screen.getByRole('button', { name: /visuals/i }).getAttribute('aria-pressed')).toBe('true');

		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /standard/i }));

		await waitFor(() => expect(screen.getByRole('button', { name: /validate brief/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /validate brief/i }));

		await waitFor(() => expect(screen.getByText(/needs edits before generation/i)).toBeTruthy());
		expect(screen.getByText(/Pick narrower subtopics before generation/i)).toBeTruthy();
		expect(screen.getByText(/Tighten each subtopic to one teachable skill/i)).toBeTruthy();
		expect(screen.getAllByText(/grade 7/i).length).toBeGreaterThan(0);
	});

	it('updates the learner summary from class-profile selections', async () => {
		render(TeacherBriefBuilder);

		await moveIntoClassProfile();
		await fireEvent.change(screen.getByLabelText(/reading level/i), {
			target: { value: 'below_grade' }
		});
		await fireEvent.change(screen.getByLabelText(/language support/i), {
			target: { value: 'many_ell' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /step-by-step support/i }));

		const learnerSummary = screen.getByLabelText(/learner summary/i) as HTMLTextAreaElement;
		expect(learnerSummary.value).toMatch(/Grade 7 learners/i);
		expect(learnerSummary.value).toMatch(/below grade level/i);
		expect(learnerSummary.value).toMatch(/many multilingual learners/i);
		expect(learnerSummary.value).toMatch(/step-by-step support/i);
	});

	it('hands a validated brief into planning and shows the review step', async () => {
		validateTeacherBrief.mockResolvedValue({
			is_ready: true,
			blockers: [],
			warnings: [],
			suggestions: []
		});
		reviewTeacherBrief.mockResolvedValue({
			coherent: true,
			warnings: []
		});
		planFromBrief.mockResolvedValue({
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
			lesson_rationale: 'Move from explanation into guided practice.',
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
					selected_components: ['hook-hero'],
					visual_policy: null,
					generation_notes: null,
					rationale: 'Open with a hook.'
				}
			],
			warning: null,
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
					learning_preferences: ['visual']
				},
				learner_context: 'Grade 7 learners are reading below grade level.',
				intended_outcome: 'practice',
				resource_type: 'worksheet',
				supports: ['worked_examples', 'step_by_step', 'visuals'],
				depth: 'standard',
				teacher_notes: ''
			},
			status: 'draft'
		});

		render(TeacherBriefBuilder);

		await completeAudienceFlow();
		await fireEvent.click(screen.getByRole('button', { name: /practice a skill/i }));
		await fireEvent.click(screen.getByRole('button', { name: /worksheet/i }));
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /standard/i }));
		await waitFor(() => expect(screen.getByRole('button', { name: /validate brief/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /validate brief/i }));
		await waitFor(() => expect(screen.getByRole('button', { name: /build plan/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /build plan/i }));

		await waitFor(() => expect(screen.getByText(/plan review/i)).toBeTruthy());
		expect(planFromBrief).toHaveBeenCalled();
		expect(screen.getByText(/start with the idea/i)).toBeTruthy();
		expect(screen.getByText(/class profile:/i)).toBeTruthy();
	});
});
