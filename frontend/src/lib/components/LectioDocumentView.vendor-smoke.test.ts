// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';

import LectioDocumentView from './LectioDocumentView.svelte';

const imagePipelineDocument = {
	generation_id: 'gen_vendor_smoke',
	subject: 'Newtonian motion',
	context: 'A vendor-smoke lesson proving hook images and diagram-series images render end-to-end.',
	template_id: 'diagram-led',
	preset_id: 'blue-classroom',
	status: 'completed',
	section_manifest: [],
	sections: [
		{
			section_id: 'sec_vendor_smoke',
			template_id: 'diagram-led',
			header: {
				title: 'Diagram-led walkthrough',
				subject: 'Physics',
				grade_band: 'secondary'
			},
			hook: {
				headline: 'The same push does not move every object equally',
				body: 'A realism image should anchor the lesson before the formal explanation starts.',
				anchor: 'mass changes how strongly a force changes motion',
				image: {
					url: '/images/hook-realism.png',
					alt: 'Generated realism hook'
				}
			},
			explanation: {
				body: 'Mass resists acceleration, so the same net force produces different changes in motion.',
				emphasis: ['Mass resists acceleration']
			},
			diagram_series: {
				title: 'Force changes motion',
				diagrams: [
					{
						step_label: 'Image step',
						caption: 'A generated step image for the diagram series.',
						image_url: '/images/series-step-1.png'
					},
					{
						step_label: 'SVG step',
						caption: 'Inline SVG still works after an image-backed step.',
						svg_content:
							'<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg"><text x="12" y="44">Force applied</text></svg>'
					}
				]
			},
			practice: {
				problems: [
					{
						difficulty: 'warm',
						question: 'What happens to acceleration when the same force pushes a heavier object?',
						hints: [{ level: 1, text: 'Use F = ma.' }]
					},
					{
						difficulty: 'medium',
						question: 'What net force acts when acceleration is zero?',
						hints: [{ level: 1, text: 'Think about balanced forces.' }]
					}
				]
			},
			what_next: {
				body: 'Next we compare how changing the net force changes acceleration over time.',
				next: 'Net force over time'
			}
		}
	],
	failed_sections: [],
	qc_reports: [],
	quality_passed: true,
	error: null,
	created_at: '2026-04-07T00:00:00Z',
	updated_at: '2026-04-07T00:00:00Z',
	completed_at: '2026-04-07T00:01:00Z'
} as any;

describe('LectioDocumentView vendor smoke', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders vendored hook and diagram-series images through the real Lectio package', async () => {
		render(LectioDocumentView, {
			props: {
				document: imagePipelineDocument
			}
		});

		expect(screen.getByRole('img', { name: 'Generated realism hook' })).toBeTruthy();
		expect(
			screen.getByRole('img', { name: 'A generated step image for the diagram series.' })
		).toBeTruthy();
		expect(screen.getByText('Diagram-led walkthrough')).toBeTruthy();
		expect(screen.getByText('Force changes motion')).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /Next/i }));

		expect(screen.getByText('Step 2 of 2')).toBeTruthy();
		expect(screen.getByText('Force applied')).toBeTruthy();
	});
});
