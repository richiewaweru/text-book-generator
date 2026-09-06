<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { providePrintMode } from 'lectio';
	import LessonReadOnlyView from '$lib/builder/components/canvas/LessonReadOnlyView.svelte';
	import { getPackDocument, type CanonicalPackDocumentResponse } from '$lib/api/learning-pack';
	import type { LessonDocument } from 'lectio';
	import '$lib/builder/styles/print.css';

	providePrintMode(() => true);
	const packId = $derived(page.params.pack_id ?? '');
	const requested = $derived(new Set((page.url.searchParams.get('variants') ?? '').split(',').map((label) => label.trim()).filter(Boolean)));
	let pack = $state<CanonicalPackDocumentResponse | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const next = await getPackDocument(packId);
			pack = { ...next, resources: requested.size ? next.resources.filter((resource) => requested.has(resource.label)) : next.resources };
			if (!pack.resources.some((resource) => resource.document)) throw new Error('No canonical lesson documents are ready to print.');
		} catch (cause) { error = cause instanceof Error ? cause.message : 'Could not prepare this pack for print.'; }
	});
</script>

<svelte:head><title>{pack ? `${pack.topic} · print` : 'Pack print · Lectio'}</title></svelte:head>

<main data-print-route="canonical-pack-print" data-generation-complete={pack && !error ? 'true' : 'false'}>
	{#if error}<p class="print-error" role="alert">{error}</p>
	{:else if pack}
		{#each pack.resources as resource (resource.resource_id)}
			{#if resource.document}<section class="pack-document" aria-label={`${resource.label} lesson`}><h1>{resource.label}</h1><LessonReadOnlyView document={resource.document as LessonDocument} /></section>{/if}
		{/each}
	{:else}<p class="print-error" role="status">Loading canonical pack documents…</p>{/if}
</main>

<style>
	.pack-document { break-after: page; }
	.pack-document h1 { margin: 1rem 0 2rem; font: 500 1.5rem Fraunces, Georgia, serif; }
	.print-error { padding: 1rem; color: #b91c1c; }
</style>
