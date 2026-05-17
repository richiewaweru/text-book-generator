import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import V3PlanActions from './V3PlanActions.svelte';

describe('V3PlanActions', () => {
	it('calls approve and retry handlers', async () => {
		const onApprove = vi.fn();
		const onRegenerate = vi.fn();
		const onRetrySection = vi.fn();

		render(V3PlanActions, {
			props: {
				failedSections: ['model'],
				onApprove,
				onRegenerate,
				onRetrySection
			}
		});

		await fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
		expect(onApprove).toHaveBeenCalledTimes(1);

		await fireEvent.click(screen.getByRole('button', { name: 'Retry model' }));
		expect(onRetrySection).toHaveBeenCalledWith('model');
	});
});
