// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { pageState, getPackStatus, downloadGenerationPdf } = vi.hoisted(() => ({
	pageState: {
		params: { pack_id: 'pack-123' },
		url: new URL('http://localhost/packs/pack-123')
	},
	getPackStatus: vi.fn(),
	downloadGenerationPdf: vi.fn()
}));

vi.mock('$app/state', () => ({
	page: pageState
}));

vi.mock('$lib/api/learning-pack', () => ({
	getPackStatus
}));

vi.mock('$lib/api/client', () => ({
	downloadGenerationPdf
}));

vi.mock('$lib/navigation/textbook', () => ({
	getTextbookRoute: (id: string) => `/textbook/${id}`
}));

import PacksPage from './+page.svelte';

function buildStatus(overrides: Record<string, unknown> = {}) {
	return {
		pack_id: 'pack-123',
		status: 'complete',
		learning_job_type: 'introduce',
		subject: 'Math',
		topic: 'Algebra',
		resource_count: 3,
		completed_count: 2,
		current_phase: null,
		current_resource_label: null,
		resources: [
			{
				resource_id: 'res-1',
				generation_id: 'gen-a',
				label: 'Resource A',
				resource_type: 'textbook',
				status: 'completed',
				phase: 'done'
			},
			{
				resource_id: 'res-2',
				generation_id: 'gen-b',
				label: 'Resource B',
				resource_type: 'reference_sheet',
				status: 'partial',
				phase: 'done'
			},
			{
				resource_id: 'res-3',
				generation_id: 'gen-c',
				label: 'Resource C',
				resource_type: 'worksheet',
				status: 'failed',
				phase: 'failed'
			}
		],
		created_at: '2026-05-01T00:00:00Z',
		completed_at: '2026-05-01T00:05:00Z',
		...overrides
	};
}

async function openPrintPanel() {
	await waitFor(() => expect(screen.getByRole('button', { name: /print pack/i })).toBeTruthy());
	await fireEvent.click(screen.getByRole('button', { name: /print pack/i }));
	await waitFor(() => expect(screen.getByRole('heading', { name: /print pack/i })).toBeTruthy());
}

describe('packs/[pack_id] batch print', () => {
	beforeEach(() => {
		getPackStatus.mockReset();
		downloadGenerationPdf.mockReset();
	});

	afterEach(() => {
		cleanup();
	});

	it('hides print action when pack is not complete', async () => {
		getPackStatus.mockResolvedValueOnce(
			buildStatus({
				status: 'running'
			})
		);

		render(PacksPage);

		await waitFor(() => expect(screen.getByText(/algebra/i)).toBeTruthy());
		expect(screen.queryByRole('button', { name: /print pack/i })).toBeNull();
	});

	it('hides print action when no completed or partial resources are selectable', async () => {
		getPackStatus.mockResolvedValueOnce(
			buildStatus({
				resources: [
					{
						resource_id: 'res-1',
						generation_id: 'gen-a',
						label: 'Resource A',
						resource_type: 'textbook',
						status: 'failed',
						phase: 'failed'
					}
				]
			})
		);

		render(PacksPage);

		await waitFor(() => expect(screen.getByText(/algebra/i)).toBeTruthy());
		expect(screen.queryByRole('button', { name: /print pack/i })).toBeNull();
	});

	it('preselects selectable resources and disables failed rows', async () => {
		getPackStatus.mockResolvedValueOnce(buildStatus());

		render(PacksPage);
		await openPrintPanel();

		const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
		expect(screen.getByRole('button', { name: /export 2 pdfs/i })).toBeTruthy();
		expect(checkboxes[0].checked).toBe(true);
		expect(checkboxes[1].checked).toBe(true);
		expect(checkboxes[2].disabled).toBe(true);
	});

	it('enables export only with required metadata and disables while running', async () => {
		let resolveDownload: (value: { filename: string | null; pageCount: string | null }) => void = () => {};
		downloadGenerationPdf.mockReturnValueOnce(
			new Promise((resolve) => {
				resolveDownload = resolve;
			})
		);
		getPackStatus.mockResolvedValueOnce(
			buildStatus({
				resources: [
					{
						resource_id: 'res-1',
						generation_id: 'gen-a',
						label: 'Resource A',
						resource_type: 'textbook',
						status: 'completed',
						phase: 'done'
					}
				]
			})
		);

		render(PacksPage);
		await openPrintPanel();

		const exportButton = screen.getByRole('button', { name: /export 1 pdf/i }) as HTMLButtonElement;
		expect(exportButton.disabled).toBe(true);

		await fireEvent.input(screen.getByPlaceholderText('Springfield High'), {
			target: { value: 'Riverside High' }
		});
		await fireEvent.input(screen.getByPlaceholderText('Ms. Johnson'), {
			target: { value: 'Ms. Lee' }
		});

		await waitFor(() => expect((screen.getByRole('button', { name: /export 1 pdf/i }) as HTMLButtonElement).disabled).toBe(false));
		await fireEvent.click(screen.getByRole('button', { name: /export 1 pdf/i }));

		await waitFor(() =>
			expect((screen.getByRole('button', { name: /exporting 1 of 1/i }) as HTMLButtonElement).disabled).toBe(true)
		);
		resolveDownload({ filename: 'resource-a.pdf', pageCount: '4' });
		await waitFor(() => expect(screen.getByText(/done\. 1 pdf exported\./i)).toBeTruthy());
	});

	it('applies student preset with include_answers false', async () => {
		downloadGenerationPdf.mockResolvedValue({ filename: null, pageCount: null });
		getPackStatus.mockResolvedValueOnce(
			buildStatus({
				resources: [
					{
						resource_id: 'res-1',
						generation_id: 'gen-a',
						label: 'Resource A',
						resource_type: 'textbook',
						status: 'completed',
						phase: 'done'
					}
				]
			})
		);

		render(PacksPage);
		await openPrintPanel();
		await fireEvent.input(screen.getByPlaceholderText('Springfield High'), {
			target: { value: 'Riverside High' }
		});
		await fireEvent.input(screen.getByPlaceholderText('Ms. Johnson'), {
			target: { value: 'Ms. Lee' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /student copy/i }));
		await fireEvent.click(screen.getByRole('button', { name: /export 1 pdf/i }));

		await waitFor(() => expect(downloadGenerationPdf).toHaveBeenCalledTimes(1));
		expect(downloadGenerationPdf).toHaveBeenCalledWith(
			'gen-a',
			expect.objectContaining({
				school_name: 'Riverside High',
				teacher_name: 'Ms. Lee',
				include_toc: true,
				include_answers: false
			})
		);
	});

	it('exports sequentially in selected order and keeps panel open on success', async () => {
		downloadGenerationPdf.mockResolvedValue({ filename: null, pageCount: null });
		getPackStatus.mockResolvedValueOnce(buildStatus());

		render(PacksPage);
		await openPrintPanel();
		await fireEvent.input(screen.getByPlaceholderText('Springfield High'), {
			target: { value: 'Riverside High' }
		});
		await fireEvent.input(screen.getByPlaceholderText('Ms. Johnson'), {
			target: { value: 'Ms. Lee' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /export 2 pdfs/i }));

		await waitFor(() => expect(downloadGenerationPdf).toHaveBeenCalledTimes(2));
		expect(downloadGenerationPdf.mock.calls[0][0]).toBe('gen-a');
		expect(downloadGenerationPdf.mock.calls[1][0]).toBe('gen-b');
		expect(downloadGenerationPdf.mock.calls[0][1]).toEqual(downloadGenerationPdf.mock.calls[1][1]);
		expect(screen.getByText(/done\. 2 pdfs exported\./i)).toBeTruthy();
		expect(screen.getByRole('heading', { name: /print pack/i })).toBeTruthy();
	});

	it('stops on first failure and surfaces error', async () => {
		downloadGenerationPdf
			.mockResolvedValueOnce({ filename: null, pageCount: null })
			.mockRejectedValueOnce(new Error('Gateway timeout'));
		getPackStatus.mockResolvedValueOnce(
			buildStatus({
				resources: [
					{
						resource_id: 'res-1',
						generation_id: 'gen-a',
						label: 'Resource A',
						resource_type: 'textbook',
						status: 'completed',
						phase: 'done'
					},
					{
						resource_id: 'res-2',
						generation_id: 'gen-b',
						label: 'Resource B',
						resource_type: 'worksheet',
						status: 'partial',
						phase: 'done'
					},
					{
						resource_id: 'res-3',
						generation_id: 'gen-c',
						label: 'Resource C',
						resource_type: 'worksheet',
						status: 'completed',
						phase: 'done'
					}
				]
			})
		);

		render(PacksPage);
		await openPrintPanel();
		await fireEvent.input(screen.getByPlaceholderText('Springfield High'), {
			target: { value: 'Riverside High' }
		});
		await fireEvent.input(screen.getByPlaceholderText('Ms. Johnson'), {
			target: { value: 'Ms. Lee' }
		});
		await fireEvent.click(screen.getByRole('button', { name: /export 3 pdfs/i }));

		await waitFor(() => expect(downloadGenerationPdf).toHaveBeenCalledTimes(2));
		expect(screen.getByText(/failed on "resource b": gateway timeout/i)).toBeTruthy();
	});
});

