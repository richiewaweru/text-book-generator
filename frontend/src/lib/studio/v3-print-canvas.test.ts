import { describe, expect, it } from 'vitest';

import { mapPackSectionsToCanvas } from './v3-print-canvas';

describe('mapPackSectionsToCanvas', () => {
	it('maps pack sections into CanvasSection objects with mergedFields payload', () => {
		const source = [
			{
				section_id: 'orient',
				header: { title: 'Orientation' },
				explanation: { body: 'hello' }
			}
		];

		const canvas = mapPackSectionsToCanvas(source);
		expect(canvas).toHaveLength(1);
		expect(canvas[0]?.id).toBe('orient');
		expect(canvas[0]?.title).toBe('Orientation');
		expect(canvas[0]?.mergedFields).toEqual(source[0]);
		expect(canvas[0]?.components).toEqual([]);
	});
});

