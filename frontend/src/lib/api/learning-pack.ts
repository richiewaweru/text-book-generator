import { apiFetch } from './client';
import { ensureOk } from './errors';
import type {
	LearningJob,
	LearningPackPlan,
	PackGenerateResponse,
	PackStatusResponse
} from '$lib/types/learning-pack';

export async function interpretSituation(situation: string): Promise<LearningJob> {
	const response = await apiFetch('/api/v1/packs/interpret', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ situation })
	});
	await ensureOk(response, 'Failed to interpret teaching situation.');
	return response.json();
}

export async function planLearningPack(job: LearningJob): Promise<LearningPackPlan> {
	const response = await apiFetch('/api/v1/packs/plan', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(job)
	});
	await ensureOk(response, 'Failed to plan learning pack.');
	return response.json();
}

export async function generateLearningPack(
	packPlan: LearningPackPlan,
	situation: string
): Promise<PackGenerateResponse> {
	const response = await apiFetch('/api/v1/packs/generate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ pack_plan: packPlan, situation })
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

