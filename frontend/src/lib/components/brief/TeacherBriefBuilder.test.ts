// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
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

const { generatePack, getPackStatus, getPacks, planPackFromBrief } = vi.hoisted(() => ({
	generatePack: vi.fn(),
	getPackStatus: vi.fn(),
	getPacks: vi.fn(),
	planPackFromBrief: vi.fn()
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

vi.mock('$lib/api/learning-pack', () => ({
	planPackFromBrief,
	generatePack,
	getPackStatus,
	getPacks
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
		generatePack.mockReset();
		getPackStatus.mockReset();
		getPacks.mockReset();
		planFromBrief.mockReset();
		planPackFromBrief.mockReset();
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

	it('shows build mode split after selecting intended outcome', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);

		render(TeacherBriefBuilder);

		await moveThroughGradeAndSubtopic();
		await waitFor(() => expect(screen.getByLabelText(/reading level/i)).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /practice a skill/i }));

		await waitFor(() => expect(screen.getByRole('button', { name: /single lesson/i })).toBeTruthy());
		expect(screen.getByRole('button', { name: /learning pack/i })).toBeTruthy();
	});

	it('editing build mode resets downstream path state safely', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);

		render(TeacherBriefBuilder);

		await moveThroughGradeAndSubtopic();
		await waitFor(() => expect(screen.getByLabelText(/reading level/i)).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /understand the idea/i }));
		await fireEvent.click(screen.getByRole('button', { name: /learning pack/i }));
		await fireEvent.click(screen.getByLabelText(/vocabulary cards/i));
		await fireEvent.click(screen.getByRole('button', { name: /continue with 3 resources ->/i }));

		const buildModeStep = screen.getByRole('heading', { name: /build mode/i }).closest('section');
		if (!buildModeStep) {
			throw new Error('Expected build mode step container');
		}

		await fireEvent.click(within(buildModeStep).getByRole('button', { name: /edit/i }));
		await fireEvent.click(screen.getByRole('button', { name: /single lesson/i }));

		await waitFor(() => expect(screen.getByRole('heading', { name: /resource type/i })).toBeTruthy());
		expect(screen.queryByText(/pack composition/i)).toBeNull();
		expect(screen.queryByRole('button', { name: /continue with 3 resources ->/i })).toBeNull();
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
			warnings: [],
			feasibility: {
				subtopics_fit: true,
				depth_adequate: true,
				supports_compatible: true
			}
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
		await fireEvent.click(screen.getByRole('button', { name: /single lesson/i }));
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

	it('runs pack mode flow through composition, review, and generation', async () => {
		resolveTopic.mockResolvedValue(
			buildResolutionResult('Solving two-step equations', 'Grade 10 fit')
		);
		planPackFromBrief.mockResolvedValue({
			pack_id: 'pack-1',
			learning_job: {
				job: 'introduce',
				subject: 'Math',
				topic: 'Algebra',
				grade_level: 'grade_10',
				grade_band: 'high_school',
				objective: 'Students can understand two-step equations.',
				class_signals: ['mixed confidence'],
				assumptions: [],
				warnings: [],
				recommended_depth: 'standard',
				inferred_supports: ['worked_examples'],
				inferred_class_profile: {}
			},
			pack_learning_plan: {
				objective: 'Students can understand two-step equations.',
				success_criteria: [],
				prerequisite_skills: [],
				likely_misconceptions: [],
				shared_vocabulary: ['equation', 'inverse operation', 'variable'],
				shared_examples: []
			},
			resources: [
				{
					id: 'resource-1-mini',
					order: 1,
					resource_type: 'mini_booklet',
					intended_outcome: 'understand',
					label: 'Mini lesson',
					purpose: 'Teach from scratch.',
					depth: 'standard',
					supports: ['worked_examples'],
					enabled: true
				},
				{
					id: 'resource-2-vocab',
					order: 2,
					resource_type: 'quick_explainer',
					intended_outcome: 'understand',
					label: 'Vocabulary cards',
					purpose: 'Anchor terms.',
					depth: 'quick',
					supports: ['worked_examples'],
					enabled: true
				},
				{
					id: 'resource-3-practice',
					order: 3,
					resource_type: 'worksheet',
					intended_outcome: 'understand',
					label: 'Practice worksheet',
					purpose: 'Apply concept.',
					depth: 'standard',
					supports: ['worked_examples'],
					enabled: true
				},
				{
					id: 'resource-4-exit',
					order: 4,
					resource_type: 'exit_ticket',
					intended_outcome: 'understand',
					label: 'Exit ticket',
					purpose: 'Check understanding.',
					depth: 'quick',
					supports: ['worked_examples'],
					enabled: true
				}
			],
			pack_rationale: 'Understand pack'
		});
		generatePack.mockResolvedValue({ pack_id: 'pack-1', status: 'running' });
		getPackStatus.mockResolvedValue({
			pack_id: 'pack-1',
			status: 'running',
			learning_job_type: 'introduce',
			subject: 'Math',
			topic: 'Algebra',
			resource_count: 3,
			completed_count: 0,
			current_phase: 'queued',
			current_resource_label: 'Mini lesson',
			resources: [],
			created_at: '2026-05-01T00:00:00Z',
			completed_at: null
		});

		render(TeacherBriefBuilder);

		await moveThroughGradeAndSubtopic();
		await waitFor(() => expect(screen.getByLabelText(/reading level/i)).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /understand the idea/i }));

		await waitFor(() => expect(screen.getByRole('button', { name: /learning pack/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /learning pack/i }));

		expect(screen.getByText(/pack composition/i)).toBeTruthy();
		expect((screen.getByLabelText(/exit ticket/i) as HTMLInputElement).disabled).toBe(true);
		await fireEvent.click(screen.getByLabelText(/vocabulary cards/i));
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /continue with 3 resources ->/i })).toBeTruthy()
		);
		await fireEvent.click(screen.getByRole('button', { name: /continue with 3 resources ->/i }));

		await fireEvent.click(screen.getByRole('button', { name: /^continue$/i }));
		await fireEvent.click(screen.getByRole('button', { name: /standard/i }));

		await waitFor(() =>
			expect(screen.getByRole('heading', { name: /pack review/i })).toBeTruthy()
		);
		expect(screen.getByText(/mini lesson/i)).toBeTruthy();
		await fireEvent.click(screen.getByRole('button', { name: /generate 3 resources ->/i }));
		await waitFor(() => expect(planPackFromBrief).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(generatePack).toHaveBeenCalledTimes(1));
		expect(generatePack).toHaveBeenCalledWith(
			expect.objectContaining({
				pack_id: 'pack-1',
				resources: expect.arrayContaining([
					expect.objectContaining({ resource_type: 'quick_explainer', enabled: false }),
					expect.objectContaining({ resource_type: 'mini_booklet', enabled: true }),
					expect.objectContaining({ resource_type: 'worksheet', enabled: true }),
					expect.objectContaining({ resource_type: 'exit_ticket', enabled: true })
				])
			}),
			expect.stringContaining('Some learners struggle with word problems')
		);

		await waitFor(() => expect(screen.getByText(/generating pack/i)).toBeTruthy());
	});
});
