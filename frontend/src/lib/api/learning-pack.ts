import { apiFetch } from './client';
import { ensureOk } from './errors';
import type { TeacherBrief } from '$lib/types';
import type {
	LearningPackPlan,
	PackGenerateResponse,
	PackStatusResponse
} from '$lib/types/learning-pack';

export async function planPackFromBrief(brief: TeacherBrief): Promise<LearningPackPlan> {
	const response = await apiFetch('/api/v1/packs/plan-from-brief', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(brief)
	});
	await ensureOk(response, 'Failed to plan learning pack.');
	return response.json();
}

export async function generatePack(
	packPlan: LearningPackPlan,
	learnerContext: string
): Promise<PackGenerateResponse> {
	const response = await apiFetch('/api/v1/packs/generate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			pack_plan: packPlan,
			learner_context: learnerContext
		})
	});
	await ensureOk(response, 'Failed to start pack generation.');
	return response.json();
}

export async function getPackStatus(packId: string): Promise<PackStatusResponse> {
	const response = await apiFetch(`/api/v1/packs/${encodeURIComponent(packId)}`);
	await ensureOk(response, 'Failed to load pack status.');
	return response.json();
}

export async function getPacks(limit = 20): Promise<PackStatusResponse[]> {
	const response = await apiFetch(`/api/v1/packs?limit=${limit}`);
	await ensureOk(response, 'Failed to load packs.');
	return response.json();
}
