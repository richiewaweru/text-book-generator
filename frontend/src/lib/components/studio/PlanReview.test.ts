// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { contracts, editedSpec, emptyPlanDraft, planDraft, planningMs } from '$lib/stores/studio';
import type { PlanningGenerationSpec, StudioTemplateContract } from '$lib/types';

import PlanReview from './PlanReview.svelte';

function buildContracts(): StudioTemplateContract[] {
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
		},
		{
			id: 'classification',
			name: 'Classification',
			family: 'classification',
			intent: 'organize-knowledge',
			tagline: 'Sort ideas into a crisp set of distinctions.',
			reading_style: 'comparison-led',
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
			available_components: ['section-header', 'hook-hero', 'comparison-grid'],
			component_budget: {},
			max_per_section: {},
			default_behaviours: {},
			section_role_defaults: {
				intro: ['hook-hero'],
				compare: ['comparison-grid'],
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

function buildSpec(): PlanningGenerationSpec {
	return {
		id: 'plan-1',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		template_decision: {
			chosen_id: 'guided-concept-path',
			chosen_name: 'Guided Concept Path',
			rationale: 'Best fit.',
			fit_score: 0.92,
			alternatives: [
				{
					template_id: 'procedure',
					template_name: 'Procedure',
					fit_score: 0.73,
					why_not_chosen: 'More procedural than this brief needs.'
				}
			]
		},
		lesson_rationale: 'This structure balances explanation and practice.',
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
				role: 'practice',
				title: 'Try the method',
				objective: 'Apply the sequence.',
				focus_note: null,
				selected_components: ['practice-stack', 'diagram-block'],
				visual_policy: {
					required: true,
					intent: 'demonstrate_process',
					mode: 'image',
					goal: 'Show the steps clearly.',
					style_notes: 'Educational diagram.'
				},
				generation_notes: null,
				rationale: 'Practice follows explanation.'
			}
		],
		warning: null,
		source_brief_id: 'brief-1',
		source_brief: {
			intent: 'Teach long division',
			audience: 'Year 6',
			prior_knowledge: '',
			extra_context: '',
			signals: {
				topic_type: 'process',
				learning_outcome: 'be-able-to-do',
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
				use_visuals: true,
				print_first: false
			}
		},
		status: 'reviewed'
	};
}

describe('PlanReview', () => {
	beforeEach(() => {
		contracts.set(buildContracts());
		editedSpec.set(buildSpec());
		planDraft.set({
			...emptyPlanDraft(),
			template_decision: buildSpec().template_decision
		});
		planningMs.set(740);
	});

	afterEach(() => {
		cleanup();
	});

	it('shows only ranked alternatives rather than the full catalog', () => {
		render(PlanReview, {
			props: {
				onBack: vi.fn(),
				onCommit: vi.fn(),
				onTemplateSwap: vi.fn()
			}
		});

		expect(screen.getByRole('button', { name: /procedure/i })).toBeTruthy();
		expect(screen.queryByRole('button', { name: /classification/i })).toBeNull();
	});

	it('opens section details and persists focus-note edits into the shared spec', async () => {
		render(PlanReview, {
			props: {
				onBack: vi.fn(),
				onCommit: vi.fn(),
				onTemplateSwap: vi.fn()
			}
		});

		await fireEvent.click(screen.getByRole('button', { name: /details/i }));
		await fireEvent.input(screen.getByLabelText(/section 1 focus note/i), {
			target: { value: 'Keep the example concrete.' }
		});

		expect(get(editedSpec)?.sections[0].focus_note).toBe('Keep the example concrete.');
		expect(screen.getByText(/image diagram/i)).toBeTruthy();
	});
});
