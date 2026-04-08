import { describe, expect, it } from 'vitest';

import type { PlanningGenerationSpec, StudioTemplateContract } from '$lib/types';

import { componentsForRole, mergeAuthoredSections, swapTemplateInSpec } from './template-swap';

function buildSpec(): PlanningGenerationSpec {
	return {
		id: 'plan-1',
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		mode: 'balanced',
		template_decision: {
			chosen_id: 'guided-concept-path',
			chosen_name: 'Guided Concept Path',
			rationale: 'Best fit.',
			fit_score: 0.92,
			alternatives: []
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
		committed_budgets: {
			'practice-stack': 1
		},
		sections: [
			{
				id: 'section-1',
				order: 1,
				role: 'process',
				title: 'Show the method',
				objective: 'Teach the sequence.',
				focus_note: 'Keep the steps visible.',
				selected_components: ['explanation-block'],
				visual_policy: {
					required: true,
					intent: 'demonstrate_process',
					mode: 'svg',
					goal: 'Show the sequence clearly.',
					style_notes: 'Diagram first.'
				},
				generation_notes: null,
				rationale: 'Process section.'
			}
		],
		warning: null,
		source_brief_id: 'brief-1',
		source_brief: {
			intent: 'Teach long division',
			audience: 'Year 6',
			prior_knowledge: '',
			extra_context: '',
			mode: 'balanced',
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
		status: 'draft'
	};
}

function buildContract(): StudioTemplateContract {
	return {
		id: 'procedure',
		name: 'Procedure',
		family: 'procedure',
		intent: 'teach-procedure',
		tagline: 'Turn a repeatable procedure into a clear sequence.',
		reading_style: 'process-led',
		tags: [],
		best_for: [],
		not_ideal_for: [],
		learner_fit: [],
		subjects: [],
		interaction_level: 'light',
		lesson_flow: [],
		required_components: ['section-header', 'hook-hero'],
		optional_components: ['process-steps'],
		always_present: ['section-header', 'hook-hero', 'what-next-bridge'],
		available_components: ['section-header', 'hook-hero', 'process-steps'],
		component_budget: {
			'process-steps': 1
		},
		max_per_section: {
			'process-steps': 1
		},
		default_behaviours: {},
		section_role_defaults: {
			intro: ['hook-hero'],
			process: ['process-steps'],
			explain: ['process-steps'],
			practice: [],
			summary: ['what-next-bridge']
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
		why_this_template_exists: 'Procedure-first teaching.',
		generation_guidance: {}
	};
}

describe('mergeAuthoredSections', () => {
	it('merges teacher-authored titles by order', () => {
		const spec = buildSpec();
		const authored = [{ order: 1, title: 'My title', focus_note: 'Focus here' }];
		const merged = mergeAuthoredSections(spec, authored);
		expect(merged.sections[0].title).toBe('My title');
		expect(merged.sections[0].focus_note).toBe('Focus here');
	});

	it('drops authored edits for orders that no longer exist', () => {
		const spec = buildSpec();
		const authored = [
			{ order: 1, title: 'Keep', focus_note: null },
			{ order: 2, title: 'Orphaned', focus_note: null }
		];
		const merged = mergeAuthoredSections(spec, authored);
		expect(merged.sections).toHaveLength(1);
		expect(merged.sections[0].title).toBe('Keep');
	});

	it('uses planner title when authored title is null', () => {
		const spec = buildSpec();
		const authored = [{ order: 1, title: null, focus_note: null }];
		const merged = mergeAuthoredSections(spec, authored);
		expect(merged.sections[0].title).toBe(spec.sections[0].title);
	});
});

describe('template swap', () => {
	it('maps role defaults from the selected contract into the editable spec', () => {
		expect(componentsForRole(buildContract(), 'process')).toEqual(['process-steps']);

		const swapped = swapTemplateInSpec(buildSpec(), buildContract());

		expect(swapped.template_id).toBe('procedure');
		expect(swapped.template_decision.chosen_name).toBe('Procedure');
		expect(swapped.sections[0].selected_components).toEqual(['process-steps']);
		expect(swapped.sections[0].visual_policy).toBeNull();
	});
});
