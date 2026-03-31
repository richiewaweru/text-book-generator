// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { planBrief } = vi.hoisted(() => ({
	planBrief: vi.fn()
}));

vi.mock('lectio', () => ({
	templateRegistryMap: {
		'guided-concept-path': {
			contract: {
				name: 'Guided Concept Path'
			}
		}
	}
}));

vi.mock('$lib/api/client', () => ({
	planBrief
}));

import TeacherStudio from './TeacherStudio.svelte';

function buildBrief() {
	return {
		template_id: 'guided-concept-path',
		preset_id: 'blue-classroom',
		section_count: 3,
		sections: [
			{
				section_id: 's-01',
				position: 1,
				title: 'Start with the problem',
				focus: 'Frame the concept in a concrete situation.',
				role: null,
				required_components: [],
				optional_components: [],
				interaction_policy: null,
				diagram_policy: null,
				enrichment_enabled: false,
				continuity_notes: null
			},
			{
				section_id: 's-02',
				position: 2,
				title: 'Show the method',
				focus: 'Walk through the core idea step by step.',
				role: null,
				required_components: [],
				optional_components: [],
				interaction_policy: null,
				diagram_policy: null,
				enrichment_enabled: false,
				continuity_notes: null
			},
			{
				section_id: 's-03',
				position: 3,
				title: 'Try it together',
				focus: 'Give a focused practice pass.',
				role: null,
				required_components: [],
				optional_components: [],
				interaction_policy: null,
				diagram_policy: null,
				enrichment_enabled: false,
				continuity_notes: null
			}
		],
		warning: 'Topic is broad - consider narrowing to a single outcome.',
		rationale: 'This template balances structure and flexibility for first exposure.',
		source_brief: {
			intent: 'Teach derivatives to Year 10 students',
			audience: 'Year 10, mixed ability',
			extra_context: 'Use concrete examples.'
		}
	};
}

describe('TeacherStudio', () => {
	afterEach(() => {
		cleanup();
		planBrief.mockReset();
	});

	it('plans a lesson, shows the review state, and lets the user nudge back to the brief', async () => {
		let resolveBrief: (value: ReturnType<typeof buildBrief>) => void;
		const briefPromise = new Promise<ReturnType<typeof buildBrief>>((resolve) => {
			resolveBrief = resolve;
		});
		planBrief.mockReturnValueOnce(briefPromise);

		render(TeacherStudio, { props: { onsubmit: vi.fn() } });

		await fireEvent.input(screen.getByLabelText(/what do you want to teach or learn\?/i), {
			target: { value: 'Teach derivatives to Year 10 students' }
		});
		await fireEvent.input(screen.getByLabelText(/who is this for\?/i), {
			target: { value: 'Year 10, mixed ability' }
		});
		await fireEvent.input(screen.getByLabelText(/optional notes/i), {
			target: { value: 'Use concrete examples.' }
		});

		await fireEvent.click(screen.getByRole('button', { name: /plan this lesson/i }));
		expect(screen.getByLabelText(/planning lesson/i)).toBeTruthy();

		resolveBrief!(buildBrief());

		await waitFor(() => expect(screen.getByText('Guided Concept Path')).toBeTruthy());
		expect(screen.getByText(/topic is broad/i)).toBeTruthy();
		expect(screen.getByText(/this template balances structure and flexibility/i)).toBeTruthy();

		const titleInput = screen.getByLabelText(/section 1 title/i) as HTMLInputElement;
		await fireEvent.input(titleInput, { target: { value: 'Start with a real example' } });
		expect(titleInput.value).toBe('Start with a real example');

		await fireEvent.click(screen.getByRole('button', { name: /nudge/i }));

		expect((screen.getByLabelText(/what do you want to teach or learn\?/i) as HTMLTextAreaElement).value).toBe(
			'Teach derivatives to Year 10 students'
		);
		expect((screen.getByLabelText(/who is this for\?/i) as HTMLInputElement).value).toBe(
			'Year 10, mixed ability'
		);
		expect((screen.getByLabelText(/optional notes/i) as HTMLTextAreaElement).value).toBe(
			'Use concrete examples.'
		);
	});

	it('translates the reviewed plan into the generation request shape', async () => {
		const onsubmit = vi.fn().mockResolvedValue(undefined);
		planBrief.mockResolvedValueOnce(buildBrief());

		render(TeacherStudio, { props: { onsubmit } });

		await fireEvent.input(screen.getByLabelText(/what do you want to teach or learn\?/i), {
			target: { value: 'Teach derivatives to Year 10 students' }
		});
		await fireEvent.input(screen.getByLabelText(/who is this for\?/i), {
			target: { value: 'Year 10, mixed ability' }
		});
		await fireEvent.input(screen.getByLabelText(/optional notes/i), {
			target: { value: 'Use concrete examples.' }
		});

		await fireEvent.click(screen.getByRole('button', { name: /plan this lesson/i }));
		await waitFor(() => expect(screen.getByText('Guided Concept Path')).toBeTruthy());

		await fireEvent.input(screen.getByLabelText(/section 1 title/i), {
			target: { value: 'Start with a real example' }
		});

		await fireEvent.click(screen.getByRole('button', { name: /^generate$/i }));

		await waitFor(() => expect(onsubmit).toHaveBeenCalledTimes(1));

		const request = onsubmit.mock.calls[0][0];
		expect(request.subject).toBe('Teach derivatives to Year 10 students');
		expect(request.template_id).toBe('guided-concept-path');
		expect(request.preset_id).toBe('blue-classroom');
		expect(request.section_count).toBe(3);
		expect(request.generation_spec?.template_id).toBe('guided-concept-path');
		expect(request.generation_spec?.sections[0].title).toBe('Start with a real example');
		expect(request.context).toContain('Audience: Year 10, mixed ability');
		expect(request.context).toContain('Notes:');
		expect(request.context).toContain('Start with a real example');
		expect(request.context).toContain('Section 2: Show the method');
	});
});
