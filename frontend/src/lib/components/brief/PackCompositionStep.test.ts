// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import PackCompositionStep from './PackCompositionStep.svelte';

describe('PackCompositionStep', () => {
	it('locks required resources, toggles optional resources, and continues with enabled resources', async () => {
		const onToggle = vi.fn();
		const onContinue = vi.fn();

		render(PackCompositionStep, {
			outcome: 'understand',
			depth: 'standard',
			enabledResourceTypes: ['mini_booklet', 'quick_explainer', 'worksheet', 'exit_ticket'],
			onToggle,
			onContinue
		});

		const requiredCheckbox = screen.getByLabelText(/exit ticket/i) as HTMLInputElement;
		expect(requiredCheckbox.disabled).toBe(true);

		const optionalCheckbox = screen.getByLabelText(/vocabulary cards/i);
		await fireEvent.click(optionalCheckbox);
		expect(onToggle).toHaveBeenCalledWith('quick_explainer', false);

		await fireEvent.click(screen.getByRole('button', { name: /continue with 4 resources/i }));
		expect(onContinue).toHaveBeenCalledTimes(1);
	});
});
