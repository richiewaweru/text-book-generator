<script lang="ts">
	import { page } from '$app/state';
	import { providePrintMode } from 'lectio';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const isPrintMode = $derived(page.url.searchParams.get('print') === 'true');
	providePrintMode(() => isPrintMode);

	/** Ready on first paint — document was loaded in +page.server.ts (SSR / Playwright). */
	const complete = true;
</script>

<svelte:head>
	<title>Studio print</title>
</svelte:head>

<div data-generation-complete={complete ? 'true' : 'false'} class="print-canvas">
	{#if data.loadError}
		<p class="p-4 text-sm text-destructive">{data.loadError}</p>
	{:else}
		<V3Canvas sections={data.sections} stage="complete" templateId={data.templateId} />
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
