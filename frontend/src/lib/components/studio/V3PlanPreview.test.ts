import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import V3PlanPreview from './V3PlanPreview.svelte';

describe('V3PlanPreview', () => {
	it('renders structural plan details', () => {
		render(V3PlanPreview, {
			props: {
				plan: {
					lesson_mode: 'first_exposure',
					lesson_intent: {
						goal: 'By the end students can compare fractions.',
						structure_rationale: 'Start concrete then move symbolic.'
					},
					anchor: {
						example: 'splitting a pizza into 8 equal slices',
						reuse_scope: 'used in orient and practice'
					},
					sections: [
						{
							id: 'orient',
							title: 'Orient',
							role: 'orient',
							visual_required: false,
							transition_note: null,
							components: [{ slug: 'hook-hero', purpose: 'surface anchor' }]
						}
					],
					question_plan: [
						{
							question_id: 'q1',
							section_id: 'orient',
							temperature: 'warm',
							diagram_required: false
						}
					]
				}
			}
		});

		expect(screen.getByText('Structural plan')).toBeTruthy();
		expect(screen.getByText(/splitting a pizza/i)).toBeTruthy();
		expect(screen.getByText(/q1 → orient/i)).toBeTruthy();
	});
});
