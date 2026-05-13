import { describe, expect, it, vi } from 'vitest';
import type { LessonDocument } from 'lectio';

import { createDocumentStore } from './document.svelte';

vi.mock('$lib/builder/persistence/server-sync', () => ({
	ensureBuilderSyncAdapterRegistered: vi.fn(),
	flushBuilderSyncQueue: vi.fn(async () => ({ synced: 0, failed: 0, errors: [] })),
	saveLessonToServer: vi.fn(async () => {})
}));

function sampleDocument(): LessonDocument {
	return {
		version: 1,
		id: 'lesson-1',
		title: 'Fractions',
		subject: 'mathematics',
		preset_id: 'blue-classroom',
		source: 'manual',
		sections: [
			{
				id: 'section-a',
				template_id: 'open-canvas',
				title: 'Section A',
				position: 0,
				block_ids: ['block-a1', 'block-a2']
			},
			{
				id: 'section-b',
				template_id: 'open-canvas',
				title: 'Section B',
				position: 1,
				block_ids: ['block-b1']
			}
		],
		blocks: {
			'block-a1': {
				id: 'block-a1',
				component_id: 'explanation-block',
				position: 0,
				content: { body: 'A fraction is part of a whole.' }
			},
			'block-a2': {
				id: 'block-a2',
				component_id: 'practice-stack',
				position: 1,
				content: { title: 'Try it' }
			},
			'block-b1': {
				id: 'block-b1',
				component_id: 'summary-block',
				position: 0,
				content: { summary: 'Review key ideas.' }
			}
		},
		media: {},
		created_at: '2026-05-13T00:00:00.000Z',
		updated_at: '2026-05-13T00:00:00.000Z'
	};
}

describe('document store block operations', () => {
	it('adds a new block with empty content in the selected section', () => {
		const store = createDocumentStore();
		store.loadDocument(sampleDocument());

		const before = store.document!.sections[0]!.block_ids.length;
		const newBlockId = store.addBlock('section-a', 'practice-stack');
		const after = store.document!.sections[0]!.block_ids.length;

		expect(newBlockId).toBeTruthy();
		expect(after).toBe(before + 1);
		expect(store.document!.blocks[newBlockId]?.component_id).toBe('practice-stack');
	});

	it('duplicates below and delete + undo restores', () => {
		const store = createDocumentStore();
		store.loadDocument(sampleDocument());

		const duplicatedId = store.duplicateBlock('section-a', 'block-a1');
		expect(duplicatedId).toBeTruthy();
		expect(store.document!.sections[0]!.block_ids[1]).toBe(duplicatedId);
		expect(store.document!.blocks[duplicatedId]?.content).toEqual(
			store.document!.blocks['block-a1']?.content
		);

		store.removeBlock('section-a', duplicatedId);
		expect(store.document!.blocks[duplicatedId]).toBeUndefined();

		store.undo();
		expect(store.document!.blocks[duplicatedId]).toBeDefined();
	});

	it('reorders blocks across sections', () => {
		const store = createDocumentStore();
		store.loadDocument(sampleDocument());

		store.moveBlock('section-a', 'section-b', 'block-a2', 1);
		expect(store.document!.sections[0]!.block_ids).toEqual(['block-a1']);
		expect(store.document!.sections[1]!.block_ids).toEqual(['block-b1', 'block-a2']);
	});
});
