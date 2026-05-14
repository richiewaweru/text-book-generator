// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '$lib/api/errors';

const { pageState, goto, logout, loadBuilderLessonWithFallback } = vi.hoisted(() => ({
	pageState: {
		params: { id: 'lesson-123' },
		url: new URL('http://localhost/builder/lesson-123')
	},
	goto: vi.fn(),
	logout: vi.fn(),
	loadBuilderLessonWithFallback: vi.fn()
}));

const mockStore = {
	document: null as Record<string, unknown> | null,
	selectedSectionId: null as string | null,
	selectedBlockId: null as string | null,
	editingBlockId: null as string | null,
	orderedSections: [] as Array<{ id: string; title: string }>,
	saveStatus: 'saved' as 'saved' | 'saving' | 'error',
	loadDocument(doc: Record<string, unknown>) {
		this.document = doc;
	},
	undo: vi.fn(),
	redo: vi.fn(),
	flushSave: vi.fn(),
	stopEditing: vi.fn(),
	deselectBlock: vi.fn(),
	startEditing: vi.fn(),
	duplicateBlock: vi.fn(),
	getSectionIdForBlock: vi.fn(() => null),
	removeBlock: vi.fn(),
	selectBlock: vi.fn()
};

vi.mock('$app/environment', () => ({
	browser: false
}));

vi.mock('$app/state', () => ({
	page: pageState
}));

vi.mock('$app/navigation', () => ({
	goto
}));

vi.mock('$lib/stores/auth', () => ({
	logout
}));

vi.mock('$lib/builder/persistence/server-sync', () => ({
	loadBuilderLessonWithFallback
}));

vi.mock('$lib/builder/stores/document.svelte', () => ({
	createDocumentStore: () => mockStore
}));

vi.mock('$lib/builder/components/shell/AppShell.svelte', async () => ({
	default: (await import('./__fixtures__/MockAppShell.svelte')).default
}));

import BuilderLessonPage from './+page.svelte';

function lesson(title = 'Fractions basics') {
	return {
		id: 'lesson-123',
		title,
		subject: 'mathematics',
		preset_id: 'blue-classroom',
		sections: [],
		blocks: {},
		media: {}
	};
}

describe('builder lesson route', () => {
	beforeEach(() => {
		mockStore.document = null;
		mockStore.selectedSectionId = null;
		mockStore.selectedBlockId = null;
		mockStore.editingBlockId = null;
		mockStore.orderedSections = [];
		mockStore.saveStatus = 'saved';
		loadBuilderLessonWithFallback.mockReset();
		goto.mockReset();
		logout.mockReset();
		pageState.params.id = 'lesson-123';
	});

	afterEach(() => {
		cleanup();
	});

	it('renders builder shell when lesson loads', async () => {
		loadBuilderLessonWithFallback.mockResolvedValueOnce({
			document: lesson('Algebra review'),
			source: 'server'
		});

		render(BuilderLessonPage);

		await waitFor(() => expect(loadBuilderLessonWithFallback).toHaveBeenCalledWith('lesson-123'));
		expect((await screen.findByTestId('mock-app-shell')).textContent ?? '').toContain('Algebra review');
	});

	it('shows not found state on 404', async () => {
		loadBuilderLessonWithFallback.mockRejectedValueOnce(new ApiError(404, 'Lesson not found'));

		render(BuilderLessonPage);

		expect(await screen.findByText('Lesson not found')).toBeTruthy();
		expect(screen.getByRole('link', { name: /back to builder lessons/i }).getAttribute('href')).toBe(
			'/builder'
		);
	});

	it('redirects to login on unauthorized response', async () => {
		loadBuilderLessonWithFallback.mockRejectedValueOnce(new ApiError(401, 'Unauthorized'));

		render(BuilderLessonPage);

		await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/login', { replaceState: true }));
	});
});
