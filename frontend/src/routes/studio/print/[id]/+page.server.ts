import { PUBLIC_API_URL } from '$env/static/public';
import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
import type { CanvasSection } from '$lib/types/v3';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, url, fetch }) => {
	const generationId = params.id;
	const token = url.searchParams.get('token');

	const sections: CanvasSection[] = [];
	let templateId = 'guided-concept-path';
	let loadError: string | null = null;

	if (!generationId) {
		return { sections, templateId, loadError: 'Missing generation id.' };
	}

	const apiBase = (PUBLIC_API_URL ?? '').replace(/\/$/, '');
	if (!apiBase) {
		return {
			sections,
			templateId,
			loadError: 'Print misconfigured: PUBLIC_API_URL is not set.'
		};
	}

	const endpoint = `${apiBase}/api/v1/v3/generations/${encodeURIComponent(generationId)}/document`;

	try {
		const headers: Record<string, string> = {};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const res = await fetch(endpoint, { headers });

		if (!res.ok) {
			loadError = `Document unavailable for print (${res.status}).`;
			return { sections, templateId, loadError };
		}

		const data = (await res.json()) as { sections?: unknown[]; template_id?: string };

		if (Array.isArray(data.sections)) {
			sections.push(...mapPackSectionsToCanvas(data.sections));
		}

		if (typeof data.template_id === 'string' && data.template_id) {
			templateId = data.template_id;
		}
	} catch (e) {
		loadError = e instanceof Error ? e.message : 'Failed to load print view.';
	}

	return { sections, templateId, loadError };
};
