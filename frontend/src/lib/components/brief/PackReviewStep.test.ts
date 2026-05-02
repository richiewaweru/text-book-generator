// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import PackReviewStep from './PackReviewStep.svelte';

describe('PackReviewStep', () => {
	it('renders captured signals and fires back/generate actions', async () => {
		const onBack = vi.fn();
		const onGenerate = vi.fn();

		render(PackReviewStep, {
			brief: {
				subject: 'Math',
				topic: 'Algebra',
				subtopics: ['Solving two-step equations'],
				grade_level: 'grade_10',
				grade_band: 'high_school',
				intended_outcome: 'understand',
				supports: ['worked_examples'],
				depth: 'standard'
			},
			enabledResources: [
				{
					label: 'Mini lesson',
					resourceType: 'mini_booklet',
					purpose: 'Teach from scratch.',
					depthBehaviour: 'teacher_depth',
					required: true,
					defaultEnabled: true
				}
			],
			loading: false,
			error: null,
			onBack,
			onGenerate
		});

		expect(screen.getByText(/pack review/i)).toBeTruthy();
		expect(screen.getByText(/solving two-step equations/i)).toBeTruthy();
		expect(screen.getByRole('button', { name: /generate 1 resource ->/i })).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /back/i }));
		await fireEvent.click(screen.getByRole('button', { name: /generate 1 resource ->/i }));

		expect(onBack).toHaveBeenCalledTimes(1);
		expect(onGenerate).toHaveBeenCalledTimes(1);
	});
});
