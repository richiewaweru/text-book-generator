import { ensureOk } from '$lib/api/errors';
import type {
	BriefValidationRequest,
	BriefValidationResult,
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
