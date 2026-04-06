// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

import ProfileSetup from './ProfileSetup.svelte';
import type { ProfileCreateRequest } from '$lib/types';

describe('ProfileSetup', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders the profile sections and submits the default request shape', async () => {
		const onsubmit = vi.fn();
		render(ProfileSetup, { props: { onsubmit } });

		expect(screen.getByRole('heading', { name: /about you/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /learning preferences/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /interests/i })).toBeTruthy();
		expect(screen.getByRole('heading', { name: /background/i })).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /complete setup/i }));

		expect(onsubmit).toHaveBeenCalledWith({
			age: 16,
			education_level: 'high_school',
			interests: [],
			learning_style: 'reading_writing',
			preferred_notation: 'plain',
			prior_knowledge: '',
			goals: '',
			preferred_depth: 'standard',
			learner_description: ''
		});
	});

	it('hydrates initial data, preserves populated values, and submits edits', async () => {
		const onsubmit = vi.fn();
		const initialData: ProfileCreateRequest = {
			age: 21,
			education_level: 'undergraduate',
			interests: ['physics', 'music'],
			learning_style: 'visual',
			preferred_notation: 'math_notation',
			prior_knowledge: 'Comfortable with algebra.',
			goals: 'Prepare for calculus.',
			preferred_depth: 'deep',
			learner_description: 'Learns quickly from worked examples.'
		};

		render(ProfileSetup, {
			props: {
				onsubmit,
				initialData,
				submitLabel: 'Save Profile'
			}
		});

		expect(screen.getByDisplayValue('21')).toBeTruthy();
		expect((screen.getByLabelText(/education level/i) as HTMLSelectElement).value).toBe(
			'undergraduate'
		);
		expect((screen.getByLabelText(/how do you learn best/i) as HTMLSelectElement).value).toBe(
			'visual'
		);
		expect((screen.getByLabelText(/preferred notation/i) as HTMLSelectElement).value).toBe(
			'math_notation'
		);
		expect((screen.getByLabelText(/default depth/i) as HTMLSelectElement).value).toBe('deep');
		expect(screen.getByDisplayValue('Comfortable with algebra.')).toBeTruthy();
		expect(screen.getByDisplayValue('Prepare for calculus.')).toBeTruthy();
		expect(screen.getByDisplayValue('Learns quickly from worked examples.')).toBeTruthy();
		expect(screen.getByText('physics')).toBeTruthy();
		expect(screen.getByText('music')).toBeTruthy();

		await fireEvent.input(screen.getByLabelText(/^age$/i), {
			target: { value: '22' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

		expect(onsubmit).toHaveBeenCalledWith({
			...initialData,
			age: 22
		});
	});
});
