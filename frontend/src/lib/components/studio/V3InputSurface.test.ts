import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import V3InputSurface from './V3InputSurface.svelte';

vi.mock('$lib/api/teacher-brief', () => ({
	resolveTopic: vi.fn().mockResolvedValue({
		subject: 'Mathematics',
		topic: 'Compound area',
		candidate_subtopics: [{ id: 'a', title: 'L-shapes', description: 'Decompose into rectangles' }],
		needs_clarification: false,
		clarification_message: null
	})
}));

describe('V3InputSurface', () => {
	it('submits a comprehensive V3InputForm payload', async () => {
		const onSubmit = vi.fn();
		render(V3InputSurface, { props: { onSubmit } });

		await fireEvent.change(screen.getByLabelText('Grade level'), { target: { value: 'Grade 7' } });
		await fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Mathematics' } });
		await fireEvent.change(screen.getByLabelText('Topic'), { target: { value: 'Compound area' } });

		await fireEvent.click(screen.getByRole('button', { name: 'Build my lesson plan' }));

		expect(onSubmit).toHaveBeenCalledTimes(1);
		const payload = onSubmit.mock.calls[0][0];
		expect(payload.grade_level).toBe('Grade 7');
		expect(payload.topic).toBe('Compound area');
		expect(Array.isArray(payload.subtopics)).toBe(true);
		expect(payload.lesson_mode).toBeDefined();
		expect(payload.learner_level).toBeDefined();
	});
});

