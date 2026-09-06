import { apiFetch } from './client';
import { ensureOk } from './errors';

export interface CanonicalGenerationSummary {
	generation_id: string;
	pipeline: 'component_lectio';
	subject: string;
	context: string;
	mode: string;
	status: string;
	stage: string;
	document_present: boolean;
	quality_passed: boolean | null;
	error: string | null;
	error_type: string | null;
	error_code: string | null;
	pack_id: string | null;
	pack_resource_id: string | null;
	pack_resource_label: string | null;
	builder_id: string | null;
	created_at: string;
	completed_at: string | null;
	last_heartbeat: string | null;
}

export async function getCanonicalGenerations(
	limit = 20,
	offset = 0
): Promise<CanonicalGenerationSummary[]> {
	const response = await apiFetch(
		`/api/v1/generations?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`
	);
	await ensureOk(response, 'Failed to load generation history.');
	return response.json() as Promise<CanonicalGenerationSummary[]>;
}

export async function getCanonicalGeneration(
	generationId: string
): Promise<CanonicalGenerationSummary> {
	const response = await apiFetch(
		`/api/v1/generations/${encodeURIComponent(generationId)}`
	);
	await ensureOk(response, 'Failed to load generation.');
	return response.json() as Promise<CanonicalGenerationSummary>;
}

export async function getCanonicalGenerationStatus(
	generationId: string
): Promise<CanonicalGenerationSummary> {
	const response = await apiFetch(
		`/api/v1/generations/${encodeURIComponent(generationId)}/status`
	);
	await ensureOk(response, 'Failed to load generation status.');
	return response.json() as Promise<CanonicalGenerationSummary>;
}
