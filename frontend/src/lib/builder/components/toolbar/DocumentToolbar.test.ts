// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LessonDocument } from 'lectio';

const { getStorageEstimate, downloadLessonDocument, printDocument, downloadBuilderLessonPdf } = vi.hoisted(() => ({
	getStorageEstimate: vi.fn(),
	downloadLessonDocument: vi.fn(),
	printDocument: vi.fn(),
	downloadBuilderLessonPdf: vi.fn()
}));

vi.mock('$lib/builder/utils/storage-estimate', () => ({
	getStorageEstimate
}));

vi.mock('$lib/builder/utils/file-io', () => ({
	downloadLessonDocument
}));

vi.mock('$lib/builder/utils/pdf-export', () => ({
	printDocument,
	downloadBuilderLessonPdf
}));

import DocumentToolbar from './DocumentToolbar.svelte';

const DOCUMENT: LessonDocument = {
	version: 1,
	id: 'lesson-1',
	title: 'Fractions basics',
	subject: 'mathematics',
	preset_id: 'blue-classroom',
	source: 'manual',
	sections: [],
	blocks: {},
	media: {},
	created_at: '2026-05-13T00:00:00Z',
	updated_at: '2026-05-13T00:00:00Z'
};

describe('DocumentToolbar', () => {
	beforeEach(() => {
		getStorageEstimate.mockResolvedValue(null);
		downloadBuilderLessonPdf.mockResolvedValue({ filename: 'lesson.pdf', pageCount: '3' });
	});

	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('toggles print preview from toolbar action', async () => {
		const onTogglePrintPreview = vi.fn();

		render(DocumentToolbar, {
			document: DOCUMENT,
			lessonId: 'lesson-1',
			onTogglePrintPreview
		});

		await fireEvent.click(screen.getByTestId('toolbar-print-preview'));

		expect(onTogglePrintPreview).toHaveBeenCalledTimes(1);
	});

	it('exports teacher and student PDFs via backend endpoint helper', async () => {
		render(DocumentToolbar, {
			document: DOCUMENT,
			lessonId: 'lesson-1'
		});

		await fireEvent.click(screen.getByTestId('toolbar-export-teacher-pdf'));
		await fireEvent.click(screen.getByTestId('toolbar-export-student-pdf'));

		await waitFor(() => {
			expect(downloadBuilderLessonPdf).toHaveBeenCalledWith('lesson-1', 'teacher');
			expect(downloadBuilderLessonPdf).toHaveBeenCalledWith('lesson-1', 'student');
		});
	});

	it('shows retry save control when save status is error', async () => {
		const onRetrySave = vi.fn();

		render(DocumentToolbar, {
			document: DOCUMENT,
			lessonId: 'lesson-1',
			saveStatus: 'error',
			onRetrySave
		});

		await fireEvent.click(screen.getByTestId('toolbar-retry-save'));
		expect(onRetrySave).toHaveBeenCalledTimes(1);
	});
});
