// @vitest-environment jsdom

import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LessonGenerationReview from './LessonGenerationReview.svelte';

const api = vi.hoisted(() => ({
	reviewLessonGeneration: vi.fn(),
	getLessonGenerationProgress: vi.fn(),
	approveLessonGeneration: vi.fn(),
	retryLessonGeneration: vi.fn(),
	openLessonInBuilder: vi.fn()
}));
const goto = vi.hoisted(() => vi.fn());

vi.mock('$lib/api/units', () => api);
vi.mock('$app/navigation', () => ({ goto }));

describe('LessonGenerationReview', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});
	afterEach(cleanup);

	it('approves, polls progress, and opens Builder without Studio navigation', async () => {
		api.reviewLessonGeneration.mockResolvedValue({ generation_id: 'gen-1', pipeline: 'component_lectio', stage: 'awaiting_review', document_present: false, failed_blocks: [], retryable: false, display_title: 'Photosynthesis', review_cards: [{ id: 'card-1', title: 'Inputs', objective: 'Name inputs', prereqs: ['cells'], misconception_descriptions: ['plants eat soil'] }] });
		api.approveLessonGeneration.mockResolvedValue({ generation_id: 'gen-1', pipeline: 'component_lectio', stage: 'complete', document_present: true, failed_blocks: [], retryable: false, builder_id: 'builder-1' });
		render(LessonGenerationReview, { unitId: 'unit-1', lessonId: 'lesson-1', generationId: 'gen-1', pathVersionId: 'path-1', pathRevision: 2 });
		await waitFor(() => expect(screen.getByRole('button', { name: /approve/i })).toBeTruthy());
		expect(screen.getByText('Inputs')).toBeTruthy();
		await fireEvent.click(screen.getByRole('button', { name: /approve/i }));
		await waitFor(() => expect(api.approveLessonGeneration).toHaveBeenCalledWith('unit-1', 'lesson-1', 'path-1', 2));
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/builder/builder-1'));
		expect(goto).not.toHaveBeenCalledWith(expect.stringContaining('/studio'));
	});

	it('keeps a failed generation in Units and retries it', async () => {
		goto.mockClear();
		api.reviewLessonGeneration.mockResolvedValue({ generation_id: 'gen-2', pipeline: 'component_lectio', stage: 'assembly_blocked', document_present: false, failed_blocks: ['check'], retryable: true });
		api.retryLessonGeneration.mockResolvedValue({ generation_id: 'gen-2', pipeline: 'component_lectio', stage: 'running', document_present: false, failed_blocks: [], retryable: true });
		render(LessonGenerationReview, { unitId: 'unit-1', lessonId: 'lesson-2', generationId: 'gen-2', pathVersionId: 'path-1', pathRevision: 2 });
		await waitFor(() => expect(screen.getByRole('button', { name: /retry writing/i })).toBeTruthy());
		await fireEvent.click(screen.getByRole('button', { name: /retry writing/i }));
		await waitFor(() => expect(api.retryLessonGeneration).toHaveBeenCalled());
		expect(goto).not.toHaveBeenCalled();
	});

	it('keeps an initially completed generation in Units until the teacher opens Builder', async () => {
		api.reviewLessonGeneration.mockResolvedValue({ generation_id: 'gen-complete', pipeline: 'component_lectio', stage: 'complete', document_present: true, failed_blocks: [], retryable: false, builder_id: 'builder-complete' });
		render(LessonGenerationReview, { unitId: 'unit-1', lessonId: 'lesson-complete', generationId: 'gen-complete', pathVersionId: 'path-1', pathRevision: 2 });

		const openButton = await screen.findByRole('button', { name: 'Open in Builder' });
		expect(goto).not.toHaveBeenCalled();
		expect(api.openLessonInBuilder).not.toHaveBeenCalled();
		await fireEvent.click(openButton);
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/builder/builder-complete'));
		expect(api.openLessonInBuilder).not.toHaveBeenCalled();
	});

	it('reports a missing Builder id instead of navigating to an invalid route', async () => {
		api.reviewLessonGeneration.mockResolvedValue({ generation_id: 'gen-3', pipeline: 'component_lectio', stage: 'complete', document_present: true, failed_blocks: [], retryable: false });
		api.openLessonInBuilder.mockResolvedValue({ builder_id: null });
		render(LessonGenerationReview, { unitId: 'unit-1', lessonId: 'lesson-3', generationId: 'gen-3', pathVersionId: 'path-1', pathRevision: 2 });
		await fireEvent.click(await screen.findByRole('button', { name: 'Open in Builder' }));
		await waitFor(() => expect(screen.getByText(/Builder lesson is not ready/i)).toBeTruthy());
		expect(goto).not.toHaveBeenCalled();
	});
});
