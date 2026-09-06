import { apiFetch } from './client';
import { ensureOk } from './errors';
import type { PackStatusResponse } from '$lib/types/learning-pack';
import type { LessonDocument } from 'lectio';

export interface CanonicalPackResourceDocument {
	resource_id: string;
	generation_id: string | null;
	label: string;
	status: string;
	document: LessonDocument | null;
}

export interface CanonicalPackDocumentResponse {
	pack_id: string;
	subject: string;
	topic: string;
	resources: CanonicalPackResourceDocument[];
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

export async function getPackDocument(packId: string): Promise<CanonicalPackDocumentResponse> {
	const response = await apiFetch(`/api/v1/packs/${encodeURIComponent(packId)}/document`);
	await ensureOk(response, 'Failed to load the canonical pack document.');
	return response.json() as Promise<CanonicalPackDocumentResponse>;
}
