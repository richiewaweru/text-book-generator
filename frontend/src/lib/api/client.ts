import type {
	BriefRequest,
	BriefResponse,
	GenerationAccepted,
	GenerationDetail,
	GenerationDocument,
	GenerationHistoryItem,
	GenerationRequest
} from '$lib/types';
import { ensureOk } from '$lib/api/errors';
import { getToken } from '$lib/stores/auth';
import { resolveClientApiBase, type ApiEnvironment } from './config';

const API_BASE = resolveClientApiBase(import.meta.env as ApiEnvironment);

export function buildApiUrl(path: string): string {
	return API_BASE ? `${API_BASE}${path}` : path;
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
	const token = getToken();
	const headers = new Headers(init?.headers);
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	return fetch(buildApiUrl(path), { ...init, headers });
}

export async function startGeneration(request: GenerationRequest): Promise<GenerationAccepted> {
	const response = await apiFetch('/api/v1/generations', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	await ensureOk(response, 'Generation failed.');
	return response.json();
}

export async function planBrief(request: BriefRequest): Promise<BriefResponse> {
	const response = await apiFetch('/api/v1/brief', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request)
	});
	await ensureOk(response, 'Brief planning failed.');
	return response.json();
}

export async function getGenerations(limit = 20, offset = 0): Promise<GenerationHistoryItem[]> {
	const response = await apiFetch(`/api/v1/generations?limit=${limit}&offset=${offset}`);
	await ensureOk(response, 'Failed to fetch generations.');
	return response.json();
}

export async function getGenerationDetail(id: string): Promise<GenerationDetail> {
	const response = await apiFetch(`/api/v1/generations/${id}`);
	await ensureOk(response, 'Failed to fetch generation detail.');
	return response.json();
}

export async function getGenerationDocument(id: string): Promise<GenerationDocument> {
	const response = await apiFetch(`/api/v1/generations/${id}/document`);
	await ensureOk(response, 'Failed to fetch document.');
	return response.json();
}

export function buildGenerationEventsUrl(id: string): string {
	const token = getToken();
	const base = buildApiUrl(`/api/v1/generations/${encodeURIComponent(id)}/events`);
	if (!token) {
		return base;
	}
	const separator = base.includes('?') ? '&' : '?';
	return `${base}${separator}token=${encodeURIComponent(token)}`;
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
	const response = await fetch(buildApiUrl('/health'));
	return response.json();
}
