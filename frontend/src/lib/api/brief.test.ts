import { afterEach, describe, expect, it, vi } from 'vitest';

const { apiFetch } = vi.hoisted(() => ({
	apiFetch: vi.fn()
}));

vi.mock('./client', () => ({
	apiFetch
}));

import { streamPlan } from './brief';

describe('studio brief API', () => {
	afterEach(() => {
		apiFetch.mockReset();
	});

	it('parses streamed planning SSE events sent over a POST response', async () => {
		apiFetch.mockResolvedValue(
			new Response(
				[
					'event: template_selected\r\n',
					'data: {"template_decision":{"chosen_id":"guided-concept-path","chosen_name":"Guided Concept Path","rationale":"Best fit.","fit_score":0.92,"alternatives":[]},"lesson_rationale":"Good for first exposure.","warning":null}\r\n\r\n',
					'event: section_planned\r\n',
					'data: {"section":{"id":"section-1","order":1,"role":"intro","title":"Start here","objective":"Frame the lesson.","focus_note":"Open with the anchor idea.","selected_components":["hook-hero"],"visual_policy":null,"generation_notes":null,"rationale":"Intro first."}}\r\n\r\n',
					'event: plan_complete\r\n',
					'data: {"spec":{"id":"plan-1","template_id":"guided-concept-path","preset_id":"blue-classroom","mode":"balanced","template_decision":{"chosen_id":"guided-concept-path","chosen_name":"Guided Concept Path","rationale":"Best fit.","fit_score":0.92,"alternatives":[]},"lesson_rationale":"Good for first exposure.","directives":{"tone_profile":"supportive","reading_level":"standard","explanation_style":"balanced","example_style":"everyday","scaffold_level":"medium","brevity":"balanced"},"committed_budgets":{"practice-stack":1},"sections":[{"id":"section-1","order":1,"role":"intro","title":"Start here","objective":"Frame the lesson.","focus_note":"Open with the anchor idea.","selected_components":["hook-hero"],"visual_policy":null,"generation_notes":null,"rationale":"Intro first."}],"warning":null,"source_brief_id":"brief-1","source_brief":{"intent":"Teach fractions","audience":"Year 5","prior_knowledge":"","extra_context":"","mode":"balanced","signals":{"topic_type":"concept","learning_outcome":"understand-why","class_style":[],"format":"both"},"preferences":{"tone":"supportive","reading_level":"standard","explanation_style":"balanced","example_style":"everyday","brevity":"balanced"},"constraints":{"more_practice":false,"keep_short":false,"use_visuals":false,"print_first":false}},"status":"draft"}}\r\n\r\n'
				].join(''),
				{
					status: 200,
					headers: {
						'Content-Type': 'text/event-stream'
					}
				}
			)
		);

		const events = [];
		for await (const event of streamPlan({
			intent: 'Teach fractions',
			audience: 'Year 5',
			prior_knowledge: '',
			extra_context: '',
			mode: 'balanced',
			signals: {
				topic_type: 'concept',
				learning_outcome: 'understand-why',
				class_style: [],
				format: 'both'
			},
			preferences: {
				tone: 'supportive',
				reading_level: 'standard',
				explanation_style: 'balanced',
				example_style: 'everyday',
				brevity: 'balanced'
			},
			constraints: {
				more_practice: false,
				keep_short: false,
				use_visuals: false,
				print_first: false
			}
		})) {
			events.push(event);
		}

		expect(events).toHaveLength(3);
		expect(events[0].event).toBe('template_selected');
		expect(events[1].event).toBe('section_planned');
		expect(events[2].event).toBe('plan_complete');
		if (events[2].event !== 'plan_complete') {
			throw new Error('Expected the final event to be plan_complete.');
		}
		expect(events[2].data.spec.sections[0].title).toBe('Start here');
		expect(events[2].data.spec.mode).toBe('balanced');
		expect(events[2].data.spec.source_brief.mode).toBe('balanced');
	});
});
