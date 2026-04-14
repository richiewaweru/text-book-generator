// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';

import LectioDocumentView from './LectioDocumentView.svelte';

const imagePipelineDocument = {
	generation_id: 'gen_vendor_smoke',
	subject: 'Newtonian motion',
	context: 'A vendor-smoke lesson proving hook, diagram-series, and diagram-compare images render end-to-end.',
	template_id: 'open-canvas',
	preset_id: 'blue-classroom',
	status: 'completed',
	section_manifest: [],
	sections: [
		{
			section_id: 'sec_vendor_smoke',
			template_id: 'open-canvas',
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
			diagram_compare: {
				before_label: 'Before push',
				after_label: 'After push',
				before_image_url: '/images/compare-before.png',
				after_image_url: '/images/compare-after.png',
				before_details: ['Net force is not yet acting.'],
				after_details: ['The net force now changes the motion.'],
				caption: 'The same scene before and after the applied force changes the motion.',
				alt_text: 'Before and after comparison showing the same object before and after a push.'
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

const simulationPipelineDocument = {
	generation_id: 'gen_vendor_simulation',
	subject: 'Probability',
	context: 'A vendor-smoke lesson proving simulation payloads render through Lectio unchanged.',
	template_id: 'open-canvas',
	preset_id: 'blue-classroom',
	status: 'completed',
	section_manifest: [],
	sections: [
		{
			section_id: 'sec_vendor_simulation',
			template_id: 'open-canvas',
			header: {
				title: 'Explore random outcomes',
				subject: 'Mathematics',
				grade_band: 'secondary'
			},
			hook: {
				headline: 'Random does not mean patternless',
				body: 'Repeated trials still produce stable distributions.',
				anchor: 'probability'
			},
			explanation: {
				body: 'Use the simulation to compare short runs with long runs.',
				emphasis: ['short runs', 'long runs']
			},
			simulation: {
				spec: {
					type: 'probability_tree',
					goal: 'Compare short and long runs',
					anchor_content: {
						headline: 'Coin flip trials'
					},
					context: {
						learner_level: 'secondary',
						template_id: 'open-canvas',
						color_mode: 'light',
						accent_color: '#17417a',
						surface_color: '#f7fbff',
						font_mono: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
					},
					dimensions: {
						width: '100%',
						height: 360,
						resizable: true
					},
					print_translation: 'static_diagram'
				},
				html_content:
					'<!DOCTYPE html><html><body><main><h1>Coin Flip Sandbox</h1><p>Heads: 8, Tails: 12</p></main></body></html>',
				fallback_diagram: {
					caption: 'Static print fallback for the simulation.',
					alt_text: 'A summary diagram of heads and tails outcomes.',
					svg_content:
						'<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg"><text x="12" y="48">Heads: 8</text><text x="12" y="84">Tails: 12</text></svg>'
				},
				explanation: 'Use the controls to compare how the distribution settles over time.'
			},
			practice: {
				problems: [
					{
						difficulty: 'warm',
						question: 'What changes as the number of trials grows?',
						hints: [{ level: 1, text: 'Look at the balance between heads and tails.' }]
					}
				]
			},
			what_next: {
				body: 'Next we connect repeated trials to expected value.',
				next: 'Expected value'
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

	it('renders vendored hook, diagram-series, and diagram-compare images through the real Lectio package', async () => {
		const { container } = render(LectioDocumentView, {
			props: {
				document: imagePipelineDocument
			}
		});

		expect(screen.getByRole('img', { name: 'Generated realism hook' })).toBeTruthy();
		expect(
			screen.getByRole('img', { name: 'A generated step image for the diagram series.' })
		).toBeTruthy();
		expect(
			container.querySelector('img[src="/images/compare-before.png"]')
		).toBeTruthy();
		expect(
			container.querySelector('img[src="/images/compare-after.png"]')
		).toBeTruthy();
		expect(screen.getByText('Diagram-led walkthrough')).toBeTruthy();
		expect(screen.getByText('Force changes motion')).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /Next/i }));

		expect(screen.getByText('Step 2 of 2')).toBeTruthy();
		expect(screen.getByText('Force applied')).toBeTruthy();

		await fireEvent.input(screen.getByLabelText('Reveal the after state'), {
			target: { value: '100' }
		});

		expect(screen.getByText('The net force now changes the motion.')).toBeTruthy();
	});

	it('renders vendored simulation payloads with live html and preserved fallback metadata', () => {
		const { container } = render(LectioDocumentView, {
			props: {
				document: simulationPipelineDocument
			}
		});

		const iframe = container.querySelector('iframe[srcdoc*="Coin Flip Sandbox"]');
		expect(iframe).toBeTruthy();
		expect(screen.getByText(/Use the controls to compare how the distribution settles over time\./i)).toBeTruthy();
		expect(screen.getByText('Explore random outcomes')).toBeTruthy();
	});
});
