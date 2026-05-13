import { describe, expect, it } from 'vitest';

import { v3PackToBuilderDocument } from './from-generation';

describe('v3PackToBuilderDocument', () => {
	it('adapts a v3 pack into a builder lesson document', () => {
		const lesson = v3PackToBuilderDocument(
			{
				generation_id: 'gen_123',
				template_id: 'guided-concept-path',
				subject: 'Fractions',
				status: 'final_ready',
				sections: [
					{
						section_id: 'section_1',
						template_id: 'guided-concept-path',
						header: {
							title: 'Fractions intro',
							subject: 'Fractions',
							grade_band: 'secondary'
						},
						hook: {
							headline: 'Why fractions matter'
						}
					}
				]
			},
			{ routeGenerationId: 'gen_123' }
		);

		expect(lesson.source).toBe('generated');
		expect(lesson.source_generation_id).toBe('gen_123');
		expect(lesson.subject).toBe('Fractions');
		expect(lesson.sections.length).toBe(1);
		expect(Object.keys(lesson.blocks).length).toBeGreaterThan(0);
	});
});