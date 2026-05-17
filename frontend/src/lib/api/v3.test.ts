import { beforeEach, describe, expect, it, vi } from 'vitest';

const { fetchEventSourceMock, capturedOptions, apiFetchMock } = vi.hoisted(() => {
	let options: Record<string, unknown> | null = null;
	return {
		fetchEventSourceMock: vi.fn((_url: string, init: Record<string, unknown>) => {
			options = init;
		}),
		apiFetchMock: vi.fn(),
		capturedOptions: {
			get current() {
				return options;
			}
		}
	};
});

vi.mock('@microsoft/fetch-event-source', () => ({
	fetchEventSource: fetchEventSourceMock
}));

vi.mock('$lib/api/client', () => ({
	apiFetch: apiFetchMock,
	buildApiUrl: (path: string) => path
}));

vi.mock('$lib/api/errors', () => ({
	ensureOk: async (response: Response, message: string) => {
		if (!response.ok) throw new Error(message);
	}
}));

import {
	approveChunkedPlan,
	connectV3StudioGenerationStream,
	fetchV3Document,
	generateBlueprint,
	getChunkedPlanStatus,
	getV3GenerationBlueprint,
	getV3GenerationDetail,
	getV3Generations
} from './v3';

describe('connectV3StudioGenerationStream', () => {
	beforeEach(() => {
		fetchEventSourceMock.mockClear();
		apiFetchMock.mockReset();
	});

	it('routes new pack events to dedicated handlers', () => {
		const onDraftPackReady = vi.fn();
		const onFinalPackReady = vi.fn();
		const onDraftStatusUpdated = vi.fn();
		const onSectionWriterFailed = vi.fn();

		connectV3StudioGenerationStream('gen-1', {
			onDraftPackReady,
			onFinalPackReady,
			onDraftStatusUpdated,
			onSectionWriterFailed
		});

		const onmessage = capturedOptions.current?.onmessage as
			| ((msg: { event?: string; data?: string }) => void)
			| undefined;
		expect(onmessage).toBeTypeOf('function');

		onmessage?.({ event: 'draft_pack_ready', data: '{"pack":{"sections":[]}}' });
		onmessage?.({ event: 'final_pack_ready', data: '{"pack":{"sections":[]}}' });
		onmessage?.({ event: 'draft_status_updated', data: '{"booklet_status":"draft_ready"}' });
		onmessage?.({
			event: 'section_writer_failed',
			data: '{"section_id":"sec-1","errors":["boom"],"warnings":[]}'
		});

		expect(onDraftPackReady).toHaveBeenCalledTimes(1);
		expect(onFinalPackReady).toHaveBeenCalledTimes(1);
		expect(onDraftStatusUpdated).toHaveBeenCalledTimes(1);
		expect(onSectionWriterFailed).toHaveBeenCalledTimes(1);
	});

	it('fetches persisted V3 document payload from API', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => ({
				kind: 'v3_booklet_pack',
				sections: [{ section_id: 's-1' }]
			})
		});

		const doc = await fetchV3Document('gen-1');
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/generations/gen-1/document', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		expect(doc.sections).toHaveLength(1);
	});

	it('loads V3 generation history from the V3 endpoint', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => [{ id: 'gen-1', status: 'completed' }]
		});

		const rows = await getV3Generations();
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/generations?limit=20&offset=0', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		expect(rows).toHaveLength(1);
	});

	it('loads V3 generation detail from the V3 endpoint', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => ({ id: 'gen-1', status: 'completed' })
		});

		const row = await getV3GenerationDetail('gen-1');
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/generations/gen-1', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		expect(row.id).toBe('gen-1');
	});

	it('sends architect_mode when generating a blueprint', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => ({ blueprint_id: 'bp-1' })
		});

		await generateBlueprint({
			signals: {
				topic: 'Area',
				subtopic: null,
				prior_knowledge: [],
				learner_needs: [],
				teacher_goal: 'Build confidence',
				inferred_resource_type: 'lesson',
				confidence: 'high',
				missing_signals: []
			},
			form: {
				grade_level: 'Grade 8',
				subject: 'Mathematics',
				duration_minutes: 45,
				topic: 'Compound area',
				subtopics: [],
				prior_knowledge: '',
				lesson_mode: 'first_exposure',
				lesson_mode_other: '',
				intended_outcome: 'understand',
				intended_outcome_other: '',
				learner_level: 'on_grade',
				reading_level: 'on_grade',
				language_support: 'none',
				prior_knowledge_level: 'new_topic',
				support_needs: [],
				learning_preferences: [],
				free_text: ''
			},
			clarification_answers: [],
			architect_mode: 'chunked'
		});

		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/blueprint', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: expect.any(String)
		});
		const payload = JSON.parse(apiFetchMock.mock.calls[0][1].body as string);
		expect(payload.architect_mode).toBe('chunked');
	});

	it('routes chunked stage events to handlers', () => {
		const onPlanReady = vi.fn();
		const onStage2SectionFailed = vi.fn();
		const onGenerationStarting = vi.fn();

		connectV3StudioGenerationStream('gen-1', {
			onPlanReady,
			onStage2SectionFailed,
			onGenerationStarting
		});

		const onmessage = capturedOptions.current?.onmessage as
			| ((msg: { event?: string; data?: string }) => void)
			| undefined;
		expect(onmessage).toBeTypeOf('function');

		onmessage?.({ event: 'plan_ready', data: '{"plan":{"sections":[]}}' });
		onmessage?.({ event: 'stage2_section_failed', data: '{"section_id":"model","errors":["bad"]}' });
		onmessage?.({ event: 'generation_starting', data: '{"generation_id":"gen-1"}' });

		expect(onPlanReady).toHaveBeenCalledTimes(1);
		expect(onStage2SectionFailed).toHaveBeenCalledTimes(1);
		expect(onGenerationStarting).toHaveBeenCalledTimes(1);
	});

	it('calls chunked lifecycle endpoints', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => ({ generation_id: 'gen-1', stage: 'plan_ready' })
		});

		await approveChunkedPlan('gen-1');
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/chunked/gen-1/approve', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});

		await getChunkedPlanStatus('gen-1');
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/chunked/gen-1/status', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
	});

	it('loads generation blueprint preview', async () => {
		apiFetchMock.mockResolvedValue({
			ok: true,
			json: async () => ({ blueprint_id: 'bp-1', title: 'Plan' })
		});
		const preview = await getV3GenerationBlueprint('gen-1');
		expect(apiFetchMock).toHaveBeenCalledWith('/api/v1/v3/generations/gen-1/blueprint', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		expect(preview.blueprint_id).toBe('bp-1');
	});
});
