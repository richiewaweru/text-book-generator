<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { providePrintMode } from 'lectio';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';
	import { buildApiUrl } from '$lib/api/client';
	import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
	import type { CanvasSection } from '$lib/types/v3';

	const generationId = $derived(page.params.id);
	const isPrintMode = $derived(page.url.searchParams.get('print') === 'true');
	const token = $derived(page.url.searchParams.get('token'));
	providePrintMode(() => isPrintMode);

	let sections = $state<CanvasSection[]>([]);
	let templateId = $state('guided-concept-path');
	let loadError = $state<string | null>(null);
	let complete = $state(false);

	onMount(async () => {
		try {
			if (!generationId) {
				loadError = 'Missing generation id.';
				return;
			}

			const endpoint = buildApiUrl(
				`/api/v1/v3/generations/${encodeURIComponent(generationId)}/document`
			);
			const headers: Record<string, string> = {};
			if (token) headers['Authorization'] = `Bearer ${token}`;

			const res = await fetch(endpoint, { headers });

			if (!res.ok) {
				loadError = `Document unavailable for print (${res.status}).`;
				return;
			}

			const data = (await res.json()) as { sections?: unknown[]; template_id?: string };

			if (Array.isArray(data.sections)) {
				sections = mapPackSectionsToCanvas(data.sections);
			}
			if (typeof data.template_id === 'string' && data.template_id) {
				templateId = data.template_id;
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load print view.';
		} finally {
			complete = true;
		}
	});
</script>

<svelte:head>
	<title>Studio print</title>
</svelte:head>

<div data-generation-complete={complete ? 'true' : 'false'} class="print-canvas">
	{#if loadError}
		<p class="p-4 text-sm text-destructive">{loadError}</p>
	{:else if complete}
		<V3Canvas {sections} stage="complete" {templateId} />
	{/if}
</div>

<style>
	.print-canvas {
		padding: 0;
		margin: 0;
		max-width: none;
	}
	@media print {
		.print-canvas {
			break-inside: avoid;
		}
	}
</style>
