// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { briefDraft, emptyDraft, returnToIdle, setContracts } from '$lib/stores/studio';

const { commitPlan, listContracts, streamPlan } = vi.hoisted(() => ({
	commitPlan: vi.fn(),
	listContracts: vi.fn(),
	streamPlan: vi.fn()
}));

vi.mock('$lib/api/brief', () => ({
	commitPlan,
	listContracts,
	streamPlan
}));

import TeacherStudioFlow from './TeacherStudioFlow.svelte';

function buildContracts() {
	return [
		{
			id: 'guided-concept-path',
			name: 'Guided Concept Path',
			family: 'guided-concept',
			intent: 'introduce-concept',
			tagline: 'Lead with need, then explain.',
			reading_style: 'linear-guided',
			tags: [],
			best_for: [],
			not_ideal_for: [],
			learner_fit: [],
			subjects: [],
			interaction_level: 'medium',
			lesson_flow: [],
			required_components: ['hook-hero'],
			optional_components: [],
			always_present: ['section-header', 'hook-hero'],
			available_components: ['section-header', 'hook-hero', 'diagram-block'],
			component_budget: {},
			max_per_section: {},
			default_behaviours: {},
			section_role_defaults: {
				intro: ['hook-hero'],
				explain: ['diagram-block'],
				practice: [],
				summary: []
			},
			signal_affinity: {
				topic_type: {},
				learning_outcome: {},
				class_style: {},
				format: {}
			},
			layout_notes: [],
			responsive_rules: [],
			print_rules: [],
			allowed_presets: ['blue-classroom'],
			why_this_template_exists: '',
			generation_guidance: {}
		},
		{
			id: 'procedure',
			name: 'Procedure',
			family: 'procedure',
			intent: 'teach-procedure',
			tagline: 'Keep the method visible.',
			reading_style: 'process-led',
			tags: [],
			best_for: [],
			not_ideal_for: [],
			learner_fit: [],
			subjects: [],
			interaction_level: 'light',
			lesson_flow: [],
			required_components: ['hook-hero'],
			optional_components: [],
			always_present: ['section-header', 'hook-hero'],
			available_components: ['section-header', 'hook-hero', 'process-steps'],
			component_budget: {},
			max_per_section: {},
			default_behaviours: {},
			section_role_defaults: {
				intro: ['hook-hero'],
				process: ['process-steps'],
				explain: ['process-steps'],
				practice: [],
				summary: []
			},
			signal_affinity: {
				topic_type: {},
				learning_outcome: {},
				class_style: {},
				format: {}
			},
			layout_notes: [],
			responsive_rules: [],
			print_rules: [],
			allowed_presets: ['blue-classroom'],
			why_this_template_exists: '',
			generation_guidance: {}
		}
	];
}

function buildSpec() {
	return {
		id: 'plan-1',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		mode: 'strict',
		template_decision: {
			chosen_id: 'guided-concept-path',
			chosen_name: 'Guided Concept Path',
			rationale: 'Best fit.',
			fit_score: 0.92,
			alternatives: [
				{
					template_id: 'procedure',
					template_name: 'Procedure',
					fit_score: 0.74,
					why_not_chosen: 'More procedural than this lesson needs.'
				}
			]
		},
		lesson_rationale: 'Good for first exposure.',
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
				role: 'process',
				title: 'Show the method',
				objective: 'Teach the sequence.',
				focus_note: 'Lead with the anchor question.',
				selected_components: ['explanation-block'],
				visual_policy: null,
				generation_notes: null,
				rationale: 'Process first.'
			}
		],
		warning: null,
		source_brief_id: 'brief-1',
		source_brief: {
			intent: 'Teach fractions',
			audience: 'Year 5',
			prior_knowledge: '',
			extra_context: '',
			mode: 'strict',
			signals: {
				topic_type: 'concept',
				learning_outcome: 'understand-why',
				class_style: [],
				format: 'both'
			},
			preferences: {
				tone: 'supportive',
				reading_level: 'standard',
				explanation_style: 'balanced',
				example_style: 'everyday',
				brevity: 'balanced'
			},
			constraints: {
				more_practice: false,
				keep_short: false,
				use_visuals: false,
				print_first: false
			}
		},
		status: 'draft'
	};
}

describe('TeacherStudioFlow', () => {
	beforeEach(() => {
		briefDraft.set(emptyDraft());
		returnToIdle();
		setContracts([]);
		listContracts.mockResolvedValue(buildContracts());
		commitPlan.mockReset();
	});

	afterEach(() => {
		cleanup();
		listContracts.mockReset();
		streamPlan.mockReset();
	});

	it('moves from intent capture into review and supports client-side template swap', async () => {
		let releasePlan!: () => void;
		const planGate = new Promise<void>((resolve) => {
			releasePlan = resolve;
		});

		streamPlan.mockImplementation(async function* () {
			yield {
				event: 'template_selected',
				data: {
					template_decision: buildSpec().template_decision,
					lesson_rationale: 'Good for first exposure.',
					warning: null
				}
			};
			yield {
				event: 'section_planned',
				data: {
					section: buildSpec().sections[0]
				}
			};
			await planGate;
			yield {
				event: 'plan_complete',
				data: {
					spec: buildSpec()
				}
			};
		});

		render(TeacherStudioFlow);

		await fireEvent.input(screen.getByLabelText(/what do you want to teach\?/i), {
			target: { value: 'Teach fractions' }
		});
		await fireEvent.input(screen.getByLabelText(/who is this for\?/i), {
			target: { value: 'Year 5' }
		});
		await fireEvent.change(screen.getByLabelText(/generation mode/i), {
			target: { value: 'strict' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /build lesson plan/i }));

		expect(screen.getByText(/building the lesson structure in view/i)).toBeTruthy();
		expect(streamPlan).toHaveBeenCalledWith(expect.objectContaining({ mode: 'strict' }));

		releasePlan();

		await waitFor(() => expect(screen.getByText(/approve the plan before generation/i)).toBeTruthy());
		expect(screen.getByDisplayValue('Show the method')).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /procedure/i }));

		await waitFor(() => expect(screen.getByText(/template updated during review/i)).toBeTruthy());
		expect(screen.getByText(/process steps/i)).toBeTruthy();
	});
});
