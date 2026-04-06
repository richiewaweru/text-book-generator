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
	applyTeacherProfileDefaults,
	returnToIdle,
	studioState
} from './studio';

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
		expect(get(briefDraft).mode).toBe('balanced');

		const spec = buildSpec();
		completePlanning(spec, 650);

		expect(get(studioState)).toBe('reviewing');
		expect(get(editedSpec)?.template_id).toBe('guided-concept-path');
		expect(get(editedSpec)?.mode).toBe('balanced');
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

	it('applies teacher profile defaults without overwriting authored lesson intent', () => {
		briefDraft.update((draft) => ({
			...draft,
			intent: 'Teach fractions'
		}));

		applyTeacherProfileDefaults({
			id: 'profile-1',
			user_id: 'user-1',
			teacher_role: 'teacher',
			subjects: ['mathematics'],
			default_grade_band: 'high_school',
			default_audience_description: 'Year 10 mixed-ability maths',
			curriculum_framework: 'GCSE',
			classroom_context: 'Limited devices and a wide confidence range.',
			planning_goals: 'More scaffolded first drafts.',
			school_or_org_name: 'Riverside High',
			delivery_preferences: {
				tone: 'supportive',
				reading_level: 'simple',
				explanation_style: 'concrete-first',
				example_style: 'everyday',
				brevity: 'tight',
				use_visuals: true,
				print_first: true,
				more_practice: true,
				keep_short: false
			},
			created_at: '2026-04-06T00:00:00Z',
			updated_at: '2026-04-06T00:00:00Z'
		});

		expect(get(briefDraft).intent).toBe('Teach fractions');
		expect(get(briefDraft).audience).toBe('Year 10 mixed-ability maths');
		expect(get(briefDraft).extra_context).toContain('Limited devices');
		expect(get(briefDraft).preferences.reading_level).toBe('simple');
		expect(get(briefDraft).constraints.use_visuals).toBe(true);
	});
});
