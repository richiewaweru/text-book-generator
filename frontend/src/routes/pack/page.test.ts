// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { generateLearningPack, interpretSituation, planLearningPack } = vi.hoisted(() => ({
	generateLearningPack: vi.fn(),
	interpretSituation: vi.fn(),
	planLearningPack: vi.fn()
}));

vi.mock('$lib/api/learning-pack', () => ({
	generateLearningPack,
	interpretSituation,
	planLearningPack
}));

import PackPage from './+page.svelte';

describe('pack route flow', () => {
	beforeEach(() => {
		interpretSituation.mockResolvedValue({
			job: 'introduce',
			subject: 'Science',
			topic: 'Plant Germination',
			grade_level: 'Grade 5',
			grade_band: 'mixed',
			objective: 'Students can describe plant germination.',
			class_signals: [],
			assumptions: [],
			warnings: [],
			recommended_depth: 'standard',
			inferred_supports: [],
			inferred_class_profile: {}
		});
		planLearningPack.mockResolvedValue({
			pack_id: 'pack-plan-1',
			learning_job: {
				job: 'introduce',
				subject: 'Science',
				topic: 'Plant Germination',
				grade_level: 'Grade 5',
				grade_band: 'mixed',
				objective: 'Students can describe plant germination.',
				class_signals: [],
				assumptions: [],
				warnings: [],
				recommended_depth: 'standard',
				inferred_supports: [],
				inferred_class_profile: {}
			},
			pack_learning_plan: {
				objective: 'Describe seed germination.',
				success_criteria: [],
				prerequisite_skills: [],
				likely_misconceptions: [],
				shared_vocabulary: [],
				shared_examples: []
			},
			resources: [
				{
					id: 'resource-1',
					order: 1,
					resource_type: 'mini_booklet',
					intended_outcome: 'understand',
					label: 'Mini lesson',
					purpose: 'Teach the concept.',
					depth: 'standard',
					supports: [],
					enabled: true
				}
			],
			pack_rationale: 'Introduce germination.'
		});
	});

	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('moves from situation input to review after interpret and plan complete', async () => {
		render(PackPage);

		await fireEvent.input(
			screen.getByPlaceholderText(/what are you teaching/i),
			{
				target: {
					value: 'Grade 5 first lesson on plant germination. They need simple vocabulary and visuals.'
				}
			}
		);
		await fireEvent.click(screen.getByRole('button', { name: /interpret and plan/i }));

		await waitFor(() => expect(screen.getByRole('heading', { name: /resources/i })).toBeTruthy());
		expect(screen.getByText(/mini lesson/i)).toBeTruthy();
		expect(generateLearningPack).not.toHaveBeenCalled();
	});
});
