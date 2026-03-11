import type { GenerationRequest, GenerationStatus } from '$lib/types';

const API_BASE = 'http://localhost:8000';

export interface GenerateAccepted {
	generation_id: string;
	status: string;
}

export async function startGeneration(request: GenerationRequest): Promise<GenerateAccepted> {
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

export async function fetchTextbookHtml(outputPath: string): Promise<string> {
	const response = await fetch(`${API_BASE}/api/v1/textbook/${encodeURIComponent(outputPath)}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch textbook: ${response.statusText}`);
	}
	return response.text();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
	const response = await fetch(`${API_BASE}/health`);
	return response.json();
}
