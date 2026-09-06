// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

const getUnitResource = vi.hoisted(() => vi.fn());
vi.mock('$app/state', () => ({
	page: {
		params: { id: 'unit-1', compositionId: 'composition-1' },
		url: new URL('http://test/units/unit-1/resources/composition-1')
	}
}));
vi.mock('$lib/api/units', () => ({ getUnitResource }));

import ResourcePage from './+page.svelte';

describe('/units/[id]/resources/[compositionId]', () => {
	afterEach(cleanup);

	it('loads a canonical lesson document into the read-only resource surface', async () => {
		getUnitResource.mockResolvedValue({
			id: 'composition-1', unit_id: 'unit-1', path_version_id: 'path-1', path_version: 1,
			path_revision: 1, projection: 'unit_exam', status: 'ready', lesson_ids: ['lesson-1'],
			period_ids: ['period-1'], group_ids: ['group-core'], selected_component_refs: [],
			selected_item_ids: ['item-1'], include_keys: true, template_version: 'resource-projection.v1',
			source_snapshots: [],
			document: {
				version: 1, id: 'composition-1', title: 'Projected assessment', subject: 'Science',
				grade_band: 'primary', preset_id: 'blue-classroom', source: 'generated',
				sections: [{ id: 'section-1', template_id: 'guided-concept-path', title: 'Projected assessment', position: 0, block_ids: ['block-1'] }],
				blocks: { 'block-1': { id: 'block-1', component_id: 'section-header', position: 0, content: { title: 'Where is food made?' } } },
				media: {}, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z'
			}
		});

		render(ResourcePage);
		expect(await screen.findByRole('button', { name: 'Print' })).toBeTruthy();
		expect(await screen.findByTestId('lesson-read-only')).toBeTruthy();
	});
});
