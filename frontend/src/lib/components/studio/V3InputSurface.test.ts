import { fireEvent, render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { describe, expect, it, vi } from 'vitest';

import V3InputSurface from './V3InputSurface.svelte';


describe('V3InputSurface', () => {
	it('submits a comprehensive V3InputForm payload', async () => {
		const onSubmit = vi.fn();
		render(V3InputSurface, { props: { onSubmit } });

		const gradeSelect = screen.getByLabelText('Grade level') as HTMLSelectElement;
		gradeSelect.value = 'Grade 7';
		await fireEvent.change(gradeSelect);
		await tick();

		const subjectSelect = screen.getByLabelText('Subject') as HTMLSelectElement;
		subjectSelect.value = 'Mathematics';
		await fireEvent.change(subjectSelect);
		await tick();

		const topicInput = screen.getByLabelText('Topic') as HTMLInputElement;
		topicInput.value = 'Compound area';
		await fireEvent.input(topicInput);
		await tick();

		const submit = screen.getByRole('button', { name: 'Build my lesson plan' }) as HTMLButtonElement;
		expect(submit.disabled).toBe(false);

		await fireEvent.click(submit);
		await tick();

		expect(onSubmit).toHaveBeenCalledTimes(1);
		const payload = onSubmit.mock.calls[0][0];
		expect(payload.grade_level).toBe('Grade 7');
		expect(payload.topic).toBe('Compound area');
		expect(Array.isArray(payload.subtopics)).toBe(true);
		expect(payload.lesson_mode).toBeDefined();
		expect(payload.learner_level).toBeDefined();
	});

	it('prefills form from example without calling resolveTopic', async () => {
		const onSubmit = vi.fn();
		render(V3InputSurface, { props: { onSubmit } });

		await fireEvent.click(screen.getByRole('button', { name: /Compound area · Year 9/i }));

		const gradeSelect = screen.getByLabelText('Grade level') as HTMLSelectElement;
		expect(gradeSelect.value).toBe('Grade 9');

		const topicInput = screen.getByLabelText('Topic') as HTMLInputElement;
		expect(topicInput.value).toBe('Compound area (L-shapes)');

		expect(screen.getByRole('button', { name: 'Splitting compound shapes' })).toBeTruthy();

		const submit = screen.getByRole('button', { name: 'Build my lesson plan' }) as HTMLButtonElement;
		expect(submit.disabled).toBe(false);
	});
});

