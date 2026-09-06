// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	getBuilderLesson: vi.fn(),
	logout: vi.fn()
}));

vi.mock('$app/state', () => ({ page: { params: { id: 'lesson-1' }, url: new URL('http://localhost/builder/lesson-1') } }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/builder/persistence/server-sync', () => ({
	loadBuilderLessonWithFallback: async (id: string) => ({ document: await mocks.getBuilderLesson(id), source: 'server' }),
	ensureBuilderSyncAdapterRegistered: vi.fn()
}));
vi.mock('$lib/stores/auth', () => ({ logout: mocks.logout }));
vi.mock('$lib/builder/components/shell/AppShell.svelte', async () => ({
	default: (await import('./__fixtures__/MockAppShell.svelte')).default
}));

import BuilderLessonPage from './+page.svelte';

describe('/builder/[id]', () => {
	beforeEach(() => {
		mocks.getBuilderLesson.mockReset();
		mocks.getBuilderLesson.mockResolvedValue({
			version: 1, id: 'lesson-1', title: 'Fractions basics', subject: 'Mathematics',
			sections: [{ id: 'section-1', title: 'Fractions', block_ids: [], position: 0 }], blocks: {}, media: {}
		});
	});
	afterEach(cleanup);

	it('loads and renders the canonical Builder lesson document', async () => {
		render(BuilderLessonPage);
		expect(await screen.findByText('Builder shell: Fractions basics')).toBeTruthy();
		expect(mocks.getBuilderLesson).toHaveBeenCalledWith('lesson-1');
	});

	it('does not expose legacy recovery or pack editor actions', async () => {
		render(BuilderLessonPage);
		expect(await screen.findByText('Builder shell: Fractions basics')).toBeTruthy();
		expect(screen.queryByRole('link', { name: /studio|pack|recovery/i })).toBeNull();
	});
});
