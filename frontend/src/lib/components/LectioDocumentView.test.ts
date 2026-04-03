// @vitest-environment jsdom

import { cleanup, render, screen, fireEvent } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('lectio', async () => {
	const MockLectioThemeSurface = (
		await import('./__fixtures__/MockLectioThemeSurface.svelte')
	).default;
	const MockTemplateRender = (await import('./__fixtures__/MockTemplateRender.svelte')).default;

	return {
		basePresetMap: {
			'blue-classroom': {
				id: 'blue-classroom',
				name: 'Blue Classroom'
			}
		},
		templateRegistryMap: {
			'guided-concept-path': {
				contract: {
					id: 'guided-concept-path',
					name: 'Guided Concept Path'
				},
				render: MockTemplateRender
			}
		},
		LectioThemeSurface: MockLectioThemeSurface,
		usePrintMode: () => () => false
	};
});

import LectioDocumentView from './LectioDocumentView.svelte';

describe('LectioDocumentView', () => {
	afterEach(() => {
		cleanup();
	});

	it('wraps rendered sections in the shared Lectio runtime surface using the selected preset', () => {
		render(LectioDocumentView, {
			props: {
				document: {
					generation_id: 'gen_123',
					subject: 'Derivatives',
					context: 'A first pass through rates of change',
					template_id: 'guided-concept-path',
					preset_id: 'blue-classroom',
					status: 'completed',
					section_manifest: [],
					sections: [
						{
							section_id: 'sec_1',
							header: { title: 'Why derivatives matter' },
							hook: { headline: 'How do we measure change at an instant?' }
						}
					],
					failed_sections: [],
					qc_reports: [],
					quality_passed: true,
					error: null,
					created_at: '2026-03-19T00:00:00Z',
					updated_at: '2026-03-19T00:00:00Z',
					completed_at: '2026-03-19T00:01:00Z'
				} as any
			}
		});

		expect(screen.getByTestId('lectio-theme-surface').getAttribute('data-preset')).toBe(
			'blue-classroom'
		);
		expect(screen.getByRole('heading', { name: /^Derivatives$/i })).toBeTruthy();
		expect(screen.getByText(/guided concept path/i)).toBeTruthy();
		expect(screen.getByText(/why derivatives matter/i)).toBeTruthy();
	});

	it('renders pending placeholders when section slots include in-flight sections', () => {
		render(LectioDocumentView, {
			props: {
				document: {
					generation_id: 'gen_123',
					subject: 'Derivatives',
					context: 'A first pass through rates of change',
					template_id: 'guided-concept-path',
					preset_id: 'blue-classroom',
					status: 'running',
					section_manifest: [
						{ section_id: 'sec_1', title: 'Why derivatives matter', position: 1 },
						{ section_id: 'sec_2', title: 'Instantaneous change', position: 2 }
					],
					sections: [],
					failed_sections: [],
					qc_reports: [],
					quality_passed: null,
					error: null,
					created_at: '2026-03-19T00:00:00Z',
					updated_at: '2026-03-19T00:00:00Z',
					completed_at: null
				} as any,
				sectionSlots: [
					{
						section_id: 'sec_1',
						title: 'Why derivatives matter',
						position: 1,
						status: 'pending',
						section: null
					}
				]
			}
		});

		expect(screen.getByText(/Generating section 1/i)).toBeTruthy();
		expect(screen.getByText(/Why derivatives matter/i)).toBeTruthy();
	});

	it('shows Export for Builder when completed and handler is provided', async () => {
		const onExportForBuilder = vi.fn();
		render(LectioDocumentView, {
			props: {
				document: {
					generation_id: 'gen_123',
					subject: 'Derivatives',
					context: 'A first pass through rates of change',
					template_id: 'guided-concept-path',
					preset_id: 'blue-classroom',
					status: 'completed',
					section_manifest: [],
					sections: [
						{
							section_id: 'sec_1',
							header: { title: 'Why derivatives matter' },
							hook: { headline: 'How do we measure change at an instant?' }
						}
					],
					failed_sections: [],
					qc_reports: [],
					quality_passed: true,
					error: null,
					created_at: '2026-03-19T00:00:00Z',
					updated_at: '2026-03-19T00:00:00Z',
					completed_at: '2026-03-19T00:01:00Z'
				} as any,
				onExportForBuilder
			}
		});

		const btn = screen.getByRole('button', { name: /export for builder/i });
		expect(btn).toBeTruthy();
		await fireEvent.click(btn);
		expect(onExportForBuilder).toHaveBeenCalledTimes(1);
	});

	it('does not show Export for Builder when generation is still running', () => {
		render(LectioDocumentView, {
			props: {
				document: {
					generation_id: 'gen_123',
					subject: 'Derivatives',
					context: 'Context',
					template_id: 'guided-concept-path',
					preset_id: 'blue-classroom',
					status: 'running',
					section_manifest: [],
					sections: [],
					failed_sections: [],
					qc_reports: [],
					quality_passed: null,
					error: null,
					created_at: '2026-03-19T00:00:00Z',
					updated_at: '2026-03-19T00:00:00Z',
					completed_at: null
				} as any,
				onExportForBuilder: vi.fn()
			}
		});

		expect(screen.queryByRole('button', { name: /export for builder/i })).toBeNull();
	});
});
