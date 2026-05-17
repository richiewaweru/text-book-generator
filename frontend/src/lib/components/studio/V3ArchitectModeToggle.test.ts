import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import V3ArchitectModeToggle from './V3ArchitectModeToggle.svelte';

describe('V3ArchitectModeToggle', () => {
	it('renders standard and chunked options and supports switching', async () => {
		const onChange = vi.fn();
		render(V3ArchitectModeToggle, {
			props: {
				value: 'chunked',
				onChange
			}
		});

		const standard = screen.getByRole('button', { name: 'Standard' });
		const chunked = screen.getByRole('button', { name: 'Chunked' });

		expect(standard).toBeTruthy();
		expect(chunked).toBeTruthy();
		expect(chunked.getAttribute('aria-pressed')).toBe('true');
		expect(standard.getAttribute('aria-pressed')).toBe('false');

		await fireEvent.click(standard);
		expect(onChange).toHaveBeenCalledWith('standard');
	});
});

