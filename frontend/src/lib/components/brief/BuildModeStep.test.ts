// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import BuildModeStep from './BuildModeStep.svelte';

describe('BuildModeStep', () => {
	it('renders both mode cards and emits selected mode', async () => {
		const onSelect = vi.fn();

		render(BuildModeStep, {
			selected: 'single',
			onSelect
		});

		expect(screen.getByText(/single lesson/i)).toBeTruthy();
		expect(screen.getByText(/learning pack/i)).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /learning pack/i }));
		expect(onSelect).toHaveBeenCalledWith('pack');
	});
});
