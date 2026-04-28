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

function buildResolutionResult(title: string, likelyGradeBand: string) {
	return {
		subject: 'Math',
		topic: 'Algebra',
		candidate_subtopics: [
			{
				id: title.toLowerCase().replaceAll(' ', '-'),
				title,
				description: `${title} focus`,
				likely_grade_band: likelyGradeBand
			}
		],
		needs_clarification: false,
		clarification_message: null
	};
}

async function submitTopic(value = 'Algebra') {
	await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
		target: { value }
	});
	await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));
}

async function selectGrade(label: RegExp) {
	await waitFor(() => expect(screen.getByRole('button', { name: label })).toBeTruthy());
	await fireEvent.click(screen.getByRole('button', { name: label }));
}

async function moveThroughGradeAndSubtopic() {
	await submitTopic();
	await selectGrade(/grade 10/i);
	await waitFor(() =>
		expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
	);
	await fireEvent.click(screen.getByRole('button', { name: /solving two-step equations/i }));
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
	});

	afterEach(() => {
		cleanup();
	});

	it('moves from topic to grade level without resolving subtopics yet', async () => {
		render(TeacherBriefBuilder);

		await submitTopic();

		expect(resolveTopic).not.toHaveBeenCalled();
		await waitFor(() =>
			expect(screen.getByText(/choose the main grade level for this resource/i)).toBeTruthy()
		);
		expect(
			screen.getByText(/your profile default is middle/i)
		).toBeTruthy();
	});

	it('selecting a grade resolves topic suggestions with grade_level and grade_band', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);

		render(TeacherBriefBuilder);

		await submitTopic();
		await selectGrade(/grade 10/i);

		await waitFor(() => expect(resolveTopic).toHaveBeenCalledTimes(1));
		expect(resolveTopic).toHaveBeenCalledWith(
			expect.objectContaining({
				raw_topic: 'Algebra',
				grade_level: 'grade_10',
				grade_band: 'high_school',
				class_profile: {
					reading_level: 'mixed',
					language_support: 'none',
					confidence: 'mixed',
					prior_knowledge: 'some_background',
					pacing: 'normal',
					learning_preferences: [],
					notes: 'Some learners struggle with word problems'
				}
			})
		);
		expect(resolveTopic.mock.calls[0][0].learner_context).toContain('Grade 10 learners');
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
		);
		expect(screen.getByText(/grade 10 fit/i)).toBeTruthy();
	});

	it('changing grade clears stale subtopics and re-resolves for the new grade', async () => {
		resolveTopic
			.mockResolvedValueOnce(
				buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
			)
			.mockResolvedValueOnce(
				buildResolutionResult('Algebraic patterns and expressions', 'Grade 5 fit')
			);

		render(TeacherBriefBuilder);

		await moveThroughGradeAndSubtopic();
		expect(screen.getByRole('heading', { name: /class profile/i })).toBeTruthy();

		await fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[1]);
		await selectGrade(/grade 5/i);

		await waitFor(() => expect(resolveTopic).toHaveBeenCalledTimes(2));
		expect(resolveTopic.mock.calls[1][0]).toMatchObject({
			raw_topic: 'Algebra',
			grade_level: 'grade_5',
			grade_band: 'upper_elementary'
		});
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /algebraic patterns and expressions/i })).toBeTruthy()
		);
		expect(screen.queryByRole('button', { name: /solving two-step equations/i })).toBeNull();
	});

	it('changing topic clears stale subtopics and waits for grade re-selection before resolving again', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);

		render(TeacherBriefBuilder);

		await submitTopic();
		await selectGrade(/grade 10/i);
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
		);

		await fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0]);
		await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
			target: { value: 'Geometry' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));

		expect(resolveTopic).toHaveBeenCalledTimes(1);
		await waitFor(() =>
			expect(screen.getByText(/choose the main grade level for this resource/i)).toBeTruthy()
		);
		expect(screen.queryByRole('button', { name: /solving two-step equations/i })).toBeNull();
	});

	it('shows grade level and grade band in review and plan flow', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);
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
				grade_level: 'grade_10',
				grade_band: 'high_school',
				class_profile: {
					reading_level: 'mixed',
					language_support: 'none',
					confidence: 'mixed',
					prior_knowledge: 'some_background',
					pacing: 'normal',
					learning_preferences: []
				},
				learner_context: 'Grade 10 learners Some learners struggle with word problems',
				intended_outcome: 'practice',
				resource_type: 'worksheet',
				supports: ['worked_examples'],
				depth: 'standard',
				teacher_notes: ''
			},
			status: 'draft'
		});

		render(TeacherBriefBuilder);

		await moveThroughGradeAndSubtopic();
		await waitFor(() => expect(screen.getByLabelText(/reading level/i)).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /practice a skill/i }));
		await fireEvent.click(screen.getByRole('button', { name: /worksheet/i }));
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /standard/i }));
		await waitFor(() => expect(screen.getByRole('button', { name: /validate brief/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /validate brief/i }));

		await waitFor(() => expect(screen.getAllByText(/grade 10/i).length).toBeGreaterThan(0));
		expect(screen.getByText(/^high school$/i)).toBeTruthy();

		await waitFor(() => expect(screen.getByRole('button', { name: /build plan/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /build plan/i }));

		await waitFor(() => expect(screen.getByText(/plan review/i)).toBeTruthy());
		expect(screen.getAllByText(/grade 10/i).length).toBeGreaterThan(0);
		expect(screen.getByText(/start with the idea/i)).toBeTruthy();
	});
});
