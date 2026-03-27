// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { emptyPlanDraft, planDraft } from '$lib/stores/studio';

import PlanStream from './PlanStream.svelte';

describe('PlanStream', () => {
	beforeEach(() => {
		planDraft.set(emptyPlanDraft());
	});

	afterEach(() => {
		cleanup();
	});

	it('shows arrived sections and a retry surface when planning fails mid-stream', async () => {
		planDraft.set({
			template_decision: {
				chosen_id: 'guided-concept-path',
				chosen_name: 'Guided Concept Path',
				rationale: 'Best fit.',
				fit_score: 0.91,
				alternatives: []
			},
			lesson_rationale: 'Good for explanation-first teaching.',
			warning: null,
			sections: [
				{
					id: 'section-1',
					order: 1,
					role: 'process',
					title: 'Show the method',
					objective: 'Teach the sequence.',
					focus_note: null,
					selected_components: ['process-steps'],
					visual_policy: null,
					generation_notes: null,
					rationale: 'Process first.'
				}
			],
			is_complete: false,
			error: 'Planner connection dropped.'
		});

		const onRetry = vi.fn();
		render(PlanStream, {
			props: {
				errorMessage: 'Planner connection dropped.',
				onRetry
			}
		});

		expect(screen.getByText(/something went wrong building your plan/i)).toBeTruthy();
		expect(screen.getByText('Show the method')).toBeTruthy();
		await fireEvent.click(screen.getByRole('button', { name: /try again/i }));
		expect(onRetry).toHaveBeenCalledTimes(1);
	});

	it('keeps a pending placeholder visible while more sections are still arriving', () => {
		planDraft.set({
			template_decision: {
				chosen_id: 'guided-concept-path',
				chosen_name: 'Guided Concept Path',
				rationale: 'Best fit.',
				fit_score: 0.91,
				alternatives: []
			},
			lesson_rationale: 'Good for explanation-first teaching.',
			warning: null,
			sections: [],
			is_complete: false,
			error: null
		});

		render(PlanStream);

		expect(screen.getByText(/selecting the opening section/i)).toBeTruthy();
	});
});
