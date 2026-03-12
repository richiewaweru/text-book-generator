import type { GenerationHistoryItem, GenerationRequest, GenerationStatus } from '$lib/types';
import { getToken } from '$lib/stores/auth';

const API_BASE = 'http://localhost:8000';

/**
 * Wrapper around fetch that injects the auth token.
 * All API calls should go through this function.
 */
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
	const token = getToken();
	const headers = new Headers(init?.headers);
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	return fetch(`${API_BASE}${path}`, { ...init, headers });
}

export interface GenerateAccepted {
	generation_id: string;
	status: string;
}

export async function startGeneration(request: GenerationRequest): Promise<GenerateAccepted> {
	const response = await apiFetch('/api/v1/generate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});

	if (!response.ok) {
		throw new Error(`Generation failed: ${response.statusText}`);
	}

	return response.json();
}

export async function getGenerationStatus(id: string): Promise<GenerationStatus> {
	const response = await apiFetch(`/api/v1/status/${id}`);

	if (!response.ok) {
		throw new Error(`Status check failed: ${response.statusText}`);
	}

	return response.json();
}

export async function pollUntilDone(
	id: string,
	onUpdate: (status: GenerationStatus) => void,
	intervalMs = 1500
): Promise<GenerationStatus> {
	while (true) {
		const status = await getGenerationStatus(id);
		onUpdate(status);

		if (status.status === 'completed' || status.status === 'failed') {
			return status;
		}

		await new Promise((resolve) => setTimeout(resolve, intervalMs));
	}
}

export async function getGenerations(limit = 20, offset = 0): Promise<GenerationHistoryItem[]> {
	const response = await apiFetch(`/api/v1/generations?limit=${limit}&offset=${offset}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch generations: ${response.statusText}`);
	}
	return response.json();
}

export async function fetchTextbookHtml(outputPath: string): Promise<string> {
	const response = await apiFetch(`/api/v1/textbook/${encodeURIComponent(outputPath)}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch textbook: ${response.statusText}`);
	}
	return response.text();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
	const response = await fetch(`${API_BASE}/health`);
	return response.json();
}
