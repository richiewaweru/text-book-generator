// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	getPackStatus: vi.fn(), getPackDocument: vi.fn(), openComponentLectioBuilderLesson: vi.fn(), goto: vi.fn()
}));
vi.mock('$app/state', () => ({ page: { params: { pack_id: 'pack-1' }, url: new URL('http://localhost/packs/pack-1') } }));
vi.mock('$app/navigation', () => ({ goto: mocks.goto }));
vi.mock('$lib/api/learning-pack', () => ({ getPackStatus: mocks.getPackStatus, getPackDocument: mocks.getPackDocument }));
vi.mock('$lib/builder/api/lesson-crud', () => ({ openComponentLectioBuilderLesson: mocks.openComponentLectioBuilderLesson }));

import PackPage from './+page.svelte';

describe('/packs/[pack_id]', () => {
	beforeEach(() => {
		mocks.getPackStatus.mockResolvedValue({ pack_id: 'pack-1', status: 'complete', resource_count: 1, completed_count: 1 });
		mocks.getPackDocument.mockResolvedValue({ pack_id: 'pack-1', subject: 'Science', topic: 'Cells', resources: [{ resource_id: 'r1', generation_id: 'gen-1', label: 'Core lesson', status: 'completed', document: { version: 1 } }] });
	});
	afterEach(cleanup);

	it('renders canonical resource state and no legacy editor link', async () => {
		render(PackPage);
		expect(await screen.findByText('Canonical learning pack')).toBeTruthy();
		expect(screen.getByRole('button', { name: 'Open in Builder' })).toBeTruthy();
		expect(screen.queryByRole('link', { name: /studio|legacy/i })).toBeNull();
	});
});
