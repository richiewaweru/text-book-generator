import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	apiFetch: vi.fn(),
	ensureOk: vi.fn()
}));
vi.mock('./client', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('./errors', () => ({ ensureOk: mocks.ensureOk }));

import { getPackDocument } from './learning-pack';

describe('canonical learning-pack API', () => {
	beforeEach(() => { mocks.apiFetch.mockReset(); mocks.ensureOk.mockReset(); });

	it('loads LessonDocuments through the canonical pack document endpoint', async () => {
		const payload = { pack_id: 'pack/1', subject: 'Science', topic: 'Cells', resources: [] };
		mocks.apiFetch.mockResolvedValue({ json: () => Promise.resolve(payload) });
		await expect(getPackDocument('pack/1')).resolves.toEqual(payload);
		expect(mocks.apiFetch).toHaveBeenCalledWith('/api/v1/packs/pack%2F1/document');
	});
});
