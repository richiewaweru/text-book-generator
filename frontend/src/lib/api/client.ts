import type { GenerationRequest, GenerationResponse, GenerationStatus } from '$lib/types';

const API_BASE = 'http://localhost:8000';

export async function generateTextbook(request: GenerationRequest): Promise<GenerationResponse> {
	const response = await fetch(`${API_BASE}/api/v1/generate`, {
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
	const response = await fetch(`${API_BASE}/api/v1/status/${id}`);

	if (!response.ok) {
		throw new Error(`Status check failed: ${response.statusText}`);
	}

	return response.json();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
	const response = await fetch(`${API_BASE}/health`);
	return response.json();
}
