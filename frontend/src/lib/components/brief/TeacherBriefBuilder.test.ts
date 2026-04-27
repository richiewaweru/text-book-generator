// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { resolveTopic, validateTeacherBrief } = vi.hoisted(() => ({
	resolveTopic: vi.fn(),
	validateTeacherBrief: vi.fn()
}));

const { getProfile } = vi.hoisted(() => ({
	getProfile: vi.fn()
}));

vi.mock('$lib/api/teacher-brief', () => ({
	resolveTopic,
	validateTeacherBrief
}));

vi.mock('$lib/api/profile', () => ({
	getProfile
}));

import TeacherBriefBuilder from './TeacherBriefBuilder.svelte';

describe('TeacherBriefBuilder', () => {
	beforeEach(() => {
		resolveTopic.mockReset();
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

	it('walks from topic capture to review and surfaces validation feedback', async () => {
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
		validateTeacherBrief.mockResolvedValue({
			is_ready: false,
			blockers: [{ field: 'subtopic', message: 'Pick a narrower subtopic before generation.' }],
			warnings: [{ field: 'supports', message: 'Too many supports may crowd a quick resource.' }],
			suggestions: [{ field: 'subtopic', suggestion: 'Tighten the subtopic to one teachable skill.' }]
		});

		render(TeacherBriefBuilder);

		await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
			target: { value: 'Algebra' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));

		await waitFor(() =>
			expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
		);
		await fireEvent.click(screen.getByRole('button', { name: /solving two-step equations/i }));
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

		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /standard/i }));

		await waitFor(() => expect(screen.getByRole('button', { name: /validate brief/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /validate brief/i }));

		await waitFor(() =>
			expect(screen.getByText(/needs edits before generation/i)).toBeTruthy()
		);
		expect(screen.getByText(/Pick a narrower subtopic before generation/i)).toBeTruthy();
		expect(screen.getByText(/Tighten the subtopic to one teachable skill/i)).toBeTruthy();
	}, 10000);

	it('resets the narrowed path when the topic changes', async () => {
		resolveTopic
			.mockResolvedValueOnce({
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
			})
			.mockResolvedValueOnce({
				subject: 'Science',
				topic: 'Photosynthesis',
				candidate_subtopics: [
					{
						id: 'sunlight-role',
						title: 'The role of sunlight in photosynthesis',
						description: 'Focus on how plants use sunlight.',
						likely_grade_band: 'middle school'
					}
				],
				needs_clarification: false,
				clarification_message: null
			});

		render(TeacherBriefBuilder);

		await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
			target: { value: 'Algebra' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));

		await waitFor(() =>
			expect(screen.getByRole('button', { name: /solving two-step equations/i })).toBeTruthy()
		);
		await fireEvent.click(screen.getByRole('button', { name: /solving two-step equations/i }));

		await waitFor(() =>
			expect(screen.getAllByText(/Math -> Algebra -> Solving two-step equations/i)).toHaveLength(2)
		);
		await fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0]);
		await fireEvent.input(screen.getByLabelText(/what are you teaching today\?/i), {
			target: { value: 'Photosynthesis' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /find subtopics/i }));

		await waitFor(() =>
			expect(
				screen.getByRole('button', { name: /the role of sunlight in photosynthesis/i })
			).toBeTruthy()
		);
		expect(screen.queryAllByText(/Math -> Algebra -> Solving two-step equations/i)).toHaveLength(0);
	});
});
