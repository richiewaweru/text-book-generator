import { afterEach, describe, expect, it, vi } from 'vitest';

const { authState } = vi.hoisted(() => ({
	authState: {
		token: 'test-token' as string | null
	}
}));

vi.mock('$lib/stores/auth', () => ({
	authToken: {
		subscribe(run: (value: string | null) => void) {
			run(authState.token);
			return () => {};
		}
	}
}));

import { commitPlan, planFromBrief, resolveTopic, reviewTeacherBrief } from './teacher-brief';

describe('teacher brief API helpers', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	it('posts TeacherBriefs to /api/v1/brief/plan', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
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
					lesson_rationale: 'Plan rationale',
					directives: {
						tone_profile: 'supportive',
						reading_level: 'standard',
						explanation_style: 'balanced',
						example_style: 'everyday',
						scaffold_level: 'medium',
						brevity: 'balanced'
					},
					committed_budgets: {},
					sections: [],
					warning: null,
					source_brief_id: 'brief-1',
					source_brief: {
						subject: 'Math',
						topic: 'Algebra',
						subtopics: ['Solving two-step equations'],
						grade_level: 'grade_7',
						grade_band: 'middle_school',
						class_profile: {
							reading_level: 'on_grade',
							language_support: 'none',
							confidence: 'mixed',
							prior_knowledge: 'some_background',
							pacing: 'normal',
							learning_preferences: ['visual']
						},
						learner_context: 'Grade 7 mixed ability',
						intended_outcome: 'practice',
						resource_type: 'worksheet',
						supports: ['worked_examples'],
						depth: 'standard',
						teacher_notes: ''
					},
					status: 'draft'
				}),
				{ status: 200, headers: { 'Content-Type': 'application/json' } }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await planFromBrief({
			subject: 'Math',
			topic: 'Algebra',
			subtopics: ['Solving two-step equations'],
			grade_level: 'grade_7',
			grade_band: 'middle_school',
			class_profile: {
				reading_level: 'on_grade',
				language_support: 'none',
				confidence: 'mixed',
				prior_knowledge: 'some_background',
				pacing: 'normal',
				learning_preferences: ['visual']
			},
			learner_context: 'Grade 7 mixed ability',
			intended_outcome: 'practice',
			resource_type: 'worksheet',
			supports: ['worked_examples'],
			depth: 'standard',
			teacher_notes: ''
		});

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/brief/plan');
		expect((fetchMock.mock.calls[0][1] as RequestInit).body).toContain('"resource_type":"worksheet"');
	});

	it('posts grade-aware topic resolution requests to /api/v1/brief/resolve-topic', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					subject: 'Math',
					topic: 'Algebra',
					candidate_subtopics: [],
					needs_clarification: false,
					clarification_message: null
				}),
				{ status: 200, headers: { 'Content-Type': 'application/json' } }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await resolveTopic({
			raw_topic: 'Algebra',
			grade_level: 'grade_10',
			grade_band: 'high_school',
			learner_context: 'Grade 10 algebra learners',
			class_profile: {
				reading_level: 'on_grade',
				language_support: 'none',
				confidence: 'mixed',
				prior_knowledge: 'some_background',
				pacing: 'normal',
				learning_preferences: ['visual']
			}
		});

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/brief/resolve-topic');
		expect((fetchMock.mock.calls[0][1] as RequestInit).body).toContain('"grade_level":"grade_10"');
		expect((fetchMock.mock.calls[0][1] as RequestInit).body).toContain('"grade_band":"high_school"');
	});

	it('posts TeacherBriefs to /api/v1/brief/review', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					coherent: false,
					warnings: [{ message: 'Quick depth may be too shallow.', suggestion: 'Use standard depth.' }]
				}),
				{ status: 200, headers: { 'Content-Type': 'application/json' } }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await reviewTeacherBrief({
			brief: {
				subject: 'Math',
				topic: 'Algebra',
				subtopics: ['Solving two-step equations', 'Solving one-step equations'],
				grade_level: 'grade_7',
				grade_band: 'middle_school',
				class_profile: {
					reading_level: 'below_grade',
					language_support: 'some_ell',
					confidence: 'low',
					prior_knowledge: 'new_topic',
					pacing: 'short_chunks',
					learning_preferences: ['step_by_step']
				},
				learner_context: 'Grade 7 mixed ability',
				intended_outcome: 'practice',
				resource_type: 'worksheet',
				supports: ['worked_examples'],
				depth: 'quick',
				teacher_notes: ''
			}
		});

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/brief/review');
	});

	it('posts reviewed specs to /api/v1/brief/commit', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					generation_id: 'gen-123',
					status: 'pending',
					events_url: '/api/v1/generations/gen-123/events',
					document_url: '/api/v1/generations/gen-123/document'
				}),
				{ status: 200, headers: { 'Content-Type': 'application/json' } }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await commitPlan({
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
			lesson_rationale: 'Plan rationale',
			directives: {
				tone_profile: 'supportive',
				reading_level: 'standard',
				explanation_style: 'balanced',
				example_style: 'everyday',
				scaffold_level: 'medium',
				brevity: 'balanced'
			},
			committed_budgets: {},
			sections: [],
			warning: null,
			source_brief_id: 'brief-1',
			source_brief: {
				subject: 'Math',
				topic: 'Algebra',
				subtopics: ['Solving two-step equations'],
				grade_level: 'grade_7',
				grade_band: 'middle_school',
				class_profile: {
					reading_level: 'on_grade',
					language_support: 'none',
					confidence: 'mixed',
					prior_knowledge: 'some_background',
					pacing: 'normal',
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
		});

		expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/brief/commit');
		expect((fetchMock.mock.calls[0][1] as RequestInit).body).toContain('"template_id":"guided-concept-path"');
	});
});
