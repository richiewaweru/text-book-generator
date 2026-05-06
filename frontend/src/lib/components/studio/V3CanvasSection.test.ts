import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import V3CanvasSection from './V3CanvasSection.svelte';

describe('V3CanvasSection', () => {
	it('shows inspect section toggle with merged field payload', () => {
		render(V3CanvasSection, {
			section: {
				id: 'sec-1',
				title: 'Section 1',
				teacher_labels: '',
				order: 0,
				components: [],
				visual: null,
				questions: [],
				mergedFields: { header: { title: 'Section 1' } }
			},
			templateId: 'guided-concept-path'
		});

		expect(screen.getByText('Inspect section')).toBeTruthy();
		expect(screen.getByText(/"header":/)).toBeTruthy();
	});
});

