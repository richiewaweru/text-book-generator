import { describe, expect, it } from 'vitest';

import type { CanvasSection } from '$lib/types/v3';

import { blocksForSection, mergedFieldsToBlocks, safeText } from './v3-print-fields';

describe('safeText', () => {
	it('trims strings and drops empties', () => {
		expect(safeText('  hi  ')).toBe('hi');
		expect(safeText('')).toBe('');
		expect(safeText(null)).toBe('');
		expect(safeText(42)).toBe('42');
	});
});

describe('mergedFieldsToBlocks', () => {
	it('extracts explanation body', () => {
		const blocks = mergedFieldsToBlocks({ explanation: { body: 'Hello world' } });
		expect(blocks).toEqual([{ kind: 'p', text: 'Hello world' }]);
	});

	it('extracts practice.problems', () => {
		const blocks = mergedFieldsToBlocks({
			practice: {
				problems: [{ question: 'Q1' }, { prompt: 'Q2' }]
			}
		});
		expect(blocks).toEqual([{ kind: 'ul', items: ['Q1', 'Q2'] }]);
	});

	it('extracts practice.items with prompt', () => {
		const blocks = mergedFieldsToBlocks({
			practice: {
				items: [{ prompt: 'Do this' }]
			}
		});
		expect(blocks).toEqual([{ kind: 'ul', items: ['Do this'] }]);
	});

	it('extracts diagram image_url', () => {
		const blocks = mergedFieldsToBlocks(
			{ diagram: { image_url: 'https://cdn.example/x.png', caption: 'Fig 1' } },
			'Section A'
		);
		expect(blocks).toEqual([
			{ kind: 'img', src: 'https://cdn.example/x.png', alt: 'Fig 1' }
		]);
	});

	it('returns empty for empty merged fields', () => {
		expect(mergedFieldsToBlocks({})).toEqual([]);
	});

	it('skips unknown nested objects but keeps top-level string', () => {
		const blocks = mergedFieldsToBlocks({
			explanation: { body: 'X' },
			weird_key: { nested: { deep: 1 } }
		});
		expect(blocks.some((b) => b.kind === 'p' && b.text === 'X')).toBe(true);
		expect(blocks.filter((b) => b.kind === 'p' && b.text.includes('nested'))).toHaveLength(0);
	});

	it('includes unknown top-level string as paragraph', () => {
		const blocks = mergedFieldsToBlocks({ footnote: 'See also page 2.' });
		expect(blocks).toContainEqual({ kind: 'p', text: 'See also page 2.' });
	});
});

describe('blocksForSection', () => {
	it('uses section title as diagram alt fallback', () => {
		const section: CanvasSection = {
			id: 's1',
			title: 'Intro',
			teacher_labels: '',
			order: 0,
			components: [],
			visual: null,
			questions: [],
			mergedFields: {
				diagram: { image_url: 'https://x/y.png' }
			}
		};
		const blocks = blocksForSection(section);
		expect(blocks).toEqual([{ kind: 'img', src: 'https://x/y.png', alt: 'Intro' }]);
	});
});
