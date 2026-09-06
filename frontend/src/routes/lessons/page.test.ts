// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	listBuilderLessons: vi.fn(),
	getBuilderLesson: vi.fn(),
	deleteBuilderLesson: vi.fn(),
	getCanonicalGenerations: vi.fn(),
	logout: vi.fn()
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/builder/api/lesson-crud', () => ({
	listBuilderLessons: mocks.listBuilderLessons,
	getBuilderLesson: mocks.getBuilderLesson,
	deleteBuilderLesson: mocks.deleteBuilderLesson
}));
vi.mock('$lib/api/generations', () => ({ getCanonicalGenerations: mocks.getCanonicalGenerations }));
vi.mock('$lib/stores/auth', () => ({
	authUser: { subscribe(run: (value: null) => void) { run(null); return () => undefined; } },
	logout: mocks.logout
}));

import LessonsPage from './+page.svelte';

const lessons = [
	{ id: 'generated', source_generation_id: 'gen-1', source_type: 'component_lectio', title: 'Photosynthesis', class_label: 'Year 7 Science', created_at: '2026-07-27T08:00:00Z', updated_at: '2026-07-27T10:00:00Z' },
	{ id: 'draft', source_generation_id: null, source_type: 'manual', title: 'Untitled lesson', class_label: null, created_at: '2026-07-25T07:00:00Z', updated_at: '2026-07-25T09:00:00Z' }
];

describe('/lessons', () => {
	beforeEach(() => {
		Object.values(mocks).forEach((mock) => mock.mockReset());
		mocks.listBuilderLessons.mockResolvedValue(lessons);
		mocks.getBuilderLesson.mockImplementation(async (id: string) => ({
			...lessons.find((lesson) => lesson.id === id),
			document: {
				version: 1, id, title: id, subject: 'Science',
				sections: id === 'generated' ? [{ id: 'section-1' }] : [], blocks: {}, media: {}
			}
		}));
		mocks.deleteBuilderLesson.mockResolvedValue(undefined);
		mocks.getCanonicalGenerations.mockResolvedValue([]);
	});

	afterEach(cleanup);

	it('loads canonical Builder lessons and generation history without V3 APIs', async () => {
		render(LessonsPage);
		expect(mocks.getCanonicalGenerations).toHaveBeenCalledWith(20, 0);
		expect(await screen.findByText('Ready to print')).toBeTruthy();
		expect(screen.getByRole('link', { name: 'Photosynthesis · Year 7 Science' }).getAttribute('href')).toBe('/builder/generated');
		expect(screen.getByRole('link', { name: 'Print' }).getAttribute('href')).toBe('/builder/print/generated');
		expect(screen.getByRole('link', { name: 'Continue' }).getAttribute('href')).toBe('/builder/draft');
	});

	it('shows an in-progress canonical generation and links to its active pack', async () => {
		mocks.listBuilderLessons.mockResolvedValue([]);
		mocks.getCanonicalGenerations.mockResolvedValue([
			{
				generation_id: 'generation-running', pipeline: 'component_lectio', subject: 'Science',
				context: 'Cells', mode: 'balanced', status: 'running', stage: 'component_lectio_running',
				document_present: false, quality_passed: null, error: null, error_type: null, error_code: null,
				pack_id: 'pack-1', pack_resource_id: 'resource-1', pack_resource_label: 'Cell structure',
				builder_id: null, created_at: '2026-07-27T08:00:00Z', completed_at: null,
				last_heartbeat: '2026-07-27T08:01:00Z'
			}
		]);

		render(LessonsPage);
		expect(await screen.findByText('Writing now')).toBeTruthy();
		expect(screen.getByRole('link', { name: 'Cell structure' }).getAttribute('href')).toBe('/units/pack-1');
		expect(screen.queryByText(/studio|v3/i)).toBeNull();
	});

	it('routes every new lesson action through Units', async () => {
		mocks.listBuilderLessons.mockResolvedValue([]);
		render(LessonsPage);
		await screen.findByText(/No lessons yet/);
		const primary = screen.getByRole('link', { name: '+ New lesson' });
		expect(primary.getAttribute('href')).toBe('/units');
	});

	it('confirms a draft deletion and removes the row only after success', async () => {
		vi.spyOn(window, 'confirm').mockReturnValue(true);
		render(LessonsPage);
		await screen.findByText('Drafts');
		await fireEvent.click(screen.getByText('Drafts'));
		await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
		await waitFor(() => expect(mocks.deleteBuilderLesson).toHaveBeenCalledWith('draft'));
		expect(screen.queryByRole('link', { name: 'Untitled lesson' })).toBeNull();
	});
});
