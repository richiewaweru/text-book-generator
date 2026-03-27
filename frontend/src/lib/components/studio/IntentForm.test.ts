// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { briefDraft, emptyDraft, returnToIdle } from '$lib/stores/studio';

import IntentForm from './IntentForm.svelte';

describe('IntentForm', () => {
	beforeEach(() => {
		briefDraft.set(emptyDraft());
		returnToIdle();
	});

	afterEach(() => {
		cleanup();
	});

	it('warns when no signals are selected but still submits the draft', async () => {
		const onSubmit = vi.fn();
		render(IntentForm, { props: { onSubmit } });

		await fireEvent.input(screen.getByLabelText(/what do you want to teach\?/i), {
			target: { value: 'Teach fractions' }
		});
		await fireEvent.input(screen.getByLabelText(/who is this for\?/i), {
			target: { value: 'Year 5' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /build lesson plan/i }));

		expect(onSubmit).toHaveBeenCalledTimes(1);
		expect(
			screen.getByText(/planning will fall back to defaults\. you can still continue\./i)
		).toBeTruthy();
	});

	it('persists example style selections into the shared brief draft', async () => {
		render(IntentForm, { props: { onSubmit: vi.fn() } });

		await fireEvent.click(screen.getByRole('button', { name: /tone and style preferences/i }));
		await fireEvent.change(screen.getByLabelText(/example style/i), {
			target: { value: 'academic' }
		});

		expect(get(briefDraft).preferences.example_style).toBe('academic');
	});
});
