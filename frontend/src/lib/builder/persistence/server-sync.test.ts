import { describe, expect, it, vi } from 'vitest';

const getBuilderLesson = vi.hoisted(() => vi.fn());
const saveDocument = vi.hoisted(() => vi.fn());
vi.mock('$lib/builder/api/lesson-crud', () => ({ getBuilderLesson, deleteBuilderLesson: vi.fn(), updateBuilderLesson: vi.fn() }));
vi.mock('./idb-store', () => ({ getDocument: vi.fn(), saveDocument }));
vi.mock('./sync-queue', () => ({ enqueueSync: vi.fn(), flushSyncQueue: vi.fn(), registerSyncAdapter: vi.fn() }));

import { loadBuilderLessonWithFallback } from './server-sync';

describe('Builder direct source loading', () => {
	it('loads Component Lectio records through Builder CRUD without V3 fallback', async () => {
		const document = { id: 'builder-1', title: 'Photosynthesis', sections: [] };
		getBuilderLesson.mockResolvedValue({ id: 'builder-1', source_type: 'component_lectio', source_generation_id: 'generation-1', document });
		await expect(loadBuilderLessonWithFallback('builder-1')).resolves.toEqual({ document, source: 'server' });
		expect(getBuilderLesson).toHaveBeenCalledWith('builder-1');
		expect(saveDocument).toHaveBeenCalledWith(document);
	});
});
