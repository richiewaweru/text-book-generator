<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { providePrintMode } from 'lectio';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';
	import { apiFetch } from '$lib/api/client';
	import { ensureOk } from '$lib/api/errors';
	import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
	import type { CanvasSection } from '$lib/types/v3';

	const generationId = $derived(page.params.id ?? '');
	const isPrintMode = $derived(page.url.searchParams.get('print') === 'true');
	providePrintMode(() => isPrintMode);
	let canvas = $state<CanvasSection[]>([]);
let templateId = $state('guided-concept-path');
	let complete = $state(false);
	let loadError = $state<string | null>(null);

	onMount(async () => {
		if (!generationId) return;
		try {
			const res = await apiFetch(
				`/api/v1/v3/generations/${encodeURIComponent(generationId)}/print-snapshot`
			);
			await ensureOk(res, 'Print snapshot unavailable.');
			const data = (await res.json()) as { sections?: unknown[]; template_id?: string };
			canvas = Array.isArray(data.sections) ? mapPackSectionsToCanvas(data.sections) : [];
			if (typeof data.template_id === 'string' && data.template_id) {
				templateId = data.template_id;
			}
			complete = true;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load print view.';
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
	{:else}
		<V3Canvas sections={canvas} stage="complete" {templateId} />
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
