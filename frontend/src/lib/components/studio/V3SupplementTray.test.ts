import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import V3SupplementTray from './V3SupplementTray.svelte';

describe('V3SupplementTray', () => {
	it('renders supplement cards and calls onCreatePlan', async () => {
		const onCreatePlan = vi.fn();

		render(V3SupplementTray, {
			props: {
				parentGenerationId: 'gen-parent',
				options: [
					{
						resource_type: 'exit_ticket',
						label: 'Exit Ticket',
						description: '3 quick questions.',
						best_for: 'End-of-lesson check',
						estimated_length: '5 minutes',
						cta: 'Create plan'
					}
				],
				onCreatePlan
			}
		});

		expect(screen.getByText('Exit Ticket')).toBeTruthy();
		expect(screen.getByRole('button', { name: 'Create plan' })).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: 'Create plan' }));
		expect(onCreatePlan).toHaveBeenCalledWith('exit_ticket');
	});

	it('shows unavailable reason when provided', () => {
		render(V3SupplementTray, {
			props: {
				parentGenerationId: 'gen-old',
				options: [],
				unavailableReason: 'No planning artifact for this generation.'
			}
		});

		expect(screen.getByText('No planning artifact for this generation.')).toBeTruthy();
	});
});
