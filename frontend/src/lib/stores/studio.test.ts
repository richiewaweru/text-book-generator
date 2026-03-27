import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';

import type { PlanningGenerationSpec } from '$lib/types';

import {
	beginPlanning,
	briefDraft,
	completePlanning,
	editedSpec,
	emptyDraft,
	failPlanning,
	returnToIdle,
	studioState
} from './studio';

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
				role: 'intro',
				title: 'Start here',
				objective: 'Frame the lesson.',
				focus_note: 'Open with the anchor idea.',
				selected_components: ['hook-hero'],
				visual_policy: null,
				generation_notes: null,
				rationale: 'Intro first.'
			}
		],
		warning: null,
		source_brief_id: 'brief-1',
		source_brief: emptyDraft(),
		status: 'draft'
	};
}

describe('studio store', () => {
	beforeEach(() => {
		briefDraft.set(emptyDraft());
		returnToIdle();
	});

	it('moves from planning into review with the completed spec', () => {
		beginPlanning();
		expect(get(studioState)).toBe('planning');

		const spec = buildSpec();
		completePlanning(spec, 650);

		expect(get(studioState)).toBe('reviewing');
		expect(get(editedSpec)?.template_id).toBe('guided-concept-path');
	});

	it('keeps the brief draft while resetting the stage back to idle', () => {
		briefDraft.update((draft) => ({
			...draft,
			intent: 'Teach fractions',
			audience: 'Year 5'
		}));
		beginPlanning();
		completePlanning(buildSpec(), 320);
		failPlanning('Planning fell back to defaults.');

		returnToIdle();

		expect(get(studioState)).toBe('idle');
		expect(get(briefDraft).intent).toBe('Teach fractions');
		expect(get(editedSpec)).toBeNull();
	});
});
