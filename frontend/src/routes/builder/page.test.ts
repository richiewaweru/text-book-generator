// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { listBuilderLessons } = vi.hoisted(() => ({
	listBuilderLessons: vi.fn()
}));

vi.mock('$lib/builder/api/lesson-crud', () => ({
	listBuilderLessons
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$lib/stores/auth', () => ({
	logout: vi.fn()
}));

vi.mock('$lib/api/errors', async () => {
	const actual = await vi.importActual<typeof import('$lib/api/errors')>('$lib/api/errors');
	return actual;
});

import BuilderIndexPage from './+page.svelte';

describe('builder lesson index route', () => {
	beforeEach(() => {
		listBuilderLessons.mockResolvedValue([]);
	});

	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('renders lesson list rows with source badges', async () => {
		listBuilderLessons.mockResolvedValueOnce([
			{
				id: 'lesson-1',
				source_generation_id: null,
				source_type: 'manual',
				title: 'Algebra warm-up',
				created_at: '2026-05-13T08:00:00Z',
				updated_at: '2026-05-13T09:15:00Z'
			},
			{
				id: 'lesson-2',
				source_generation_id: 'gen-1',
				source_type: 'v3_generation',
				title: 'Fractions recap',
				created_at: '2026-05-12T10:00:00Z',
				updated_at: '2026-05-12T11:00:00Z'
			}
		]);

		render(BuilderIndexPage);

		await waitFor(() => expect(listBuilderLessons).toHaveBeenCalledTimes(1));

		expect(screen.getByRole('link', { name: 'Algebra warm-up' }).getAttribute('href')).toBe(
			'/builder/lesson-1'
		);
		expect(screen.getByRole('link', { name: 'Fractions recap' }).getAttribute('href')).toBe(
			'/builder/lesson-2'
		);
		expect(screen.getByText('Manual')).toBeTruthy();
		expect(screen.getByText('From generation')).toBeTruthy();
	});

	it('shows empty state with create CTA when no lessons exist', async () => {
		render(BuilderIndexPage);

		await waitFor(() => expect(listBuilderLessons).toHaveBeenCalledTimes(1));

		expect(screen.getByText(/no editable lessons yet/i)).toBeTruthy();
		expect(screen.getByRole('link', { name: /create your first lesson/i }).getAttribute('href')).toBe(
			'/builder/new'
		);
	});
});
