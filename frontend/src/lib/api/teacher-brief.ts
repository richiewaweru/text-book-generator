import { ensureOk } from '$lib/api/errors';
import type {
	BriefValidationRequest,
	BriefValidationResult,
	GenerationAccepted,
	PlanningGenerationSpec,
	TeacherBrief,
	TopicResolutionRequest,
	TopicResolutionResult
} from '$lib/types';

import { apiFetch } from './client';

export async function resolveTopic(
	request: TopicResolutionRequest
): Promise<TopicResolutionResult> {
	const response = await apiFetch('/api/v1/brief/resolve-topic', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	await ensureOk(response, 'Topic resolution failed.');
	return response.json();
}

export async function validateTeacherBrief(
	request: BriefValidationRequest
): Promise<BriefValidationResult> {
	const response = await apiFetch('/api/v1/brief/validate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	await ensureOk(response, 'Brief validation failed.');
	return response.json();
}

export async function planFromBrief(
	brief: TeacherBrief
): Promise<PlanningGenerationSpec> {
	const response = await apiFetch('/api/v1/brief/plan', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(brief)
	});
	await ensureOk(response, 'Failed to plan from brief.');
	return response.json();
}

export async function commitPlan(spec: PlanningGenerationSpec): Promise<GenerationAccepted> {
	const response = await apiFetch('/api/v1/brief/commit', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(spec)
	});
	await ensureOk(response, 'Failed to commit lesson plan.');
	return response.json();
}
