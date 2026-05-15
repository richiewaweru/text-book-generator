import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import V3Clarification from './V3Clarification.svelte';
import type { V3ClarificationQuestion } from '$lib/types/v3';

describe('V3Clarification', () => {
	it('renders option pills and submits selected answer', async () => {
		const onAnswered = vi.fn();
		const questions: V3ClarificationQuestion[] = [
			{
				question: 'Include a recap at the start?',
				reason: 'Mixed prior knowledge',
				optional: false,
				answer_type: 'options',
				options: ['Yes, brief recap', 'No, start fresh']
			}
		];

		render(V3Clarification, { props: { questions, onAnswered } });

		const recap = screen.getByRole('button', { name: 'Yes, brief recap' });
		await fireEvent.click(recap);

		await fireEvent.click(screen.getByRole('button', { name: /Build the plan/i }));

		expect(onAnswered).toHaveBeenCalledWith([
			{ question: questions[0].question, answer: 'Yes, brief recap' }
		]);
	});

	it('disables proceed until required free-text is answered', async () => {
		const onAnswered = vi.fn();
		const questions: V3ClarificationQuestion[] = [
			{
				question: 'Any preferred real-world context?',
				reason: 'Could shape examples',
				optional: false,
				answer_type: 'free_text',
				options: []
			}
		];

		render(V3Clarification, { props: { questions, onAnswered } });

		const proceed = screen.getByRole('button', { name: /Build the plan/i }) as HTMLButtonElement;
		expect(proceed.disabled).toBe(true);

		const textarea = screen.getByPlaceholderText('Your answer…');
		await fireEvent.input(textarea, { target: { value: 'Garden design' } });
		expect(proceed.disabled).toBe(false);
	});
});
