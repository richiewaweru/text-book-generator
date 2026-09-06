<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getPackDocument, type CanonicalPackDocumentResponse } from '$lib/api/learning-pack';
	import { openComponentLectioBuilderLesson } from '$lib/builder/api/lesson-crud';

	const packId = $derived(page.params.pack_id ?? '');
	let pack = $state<CanonicalPackDocumentResponse | null>(null);
	let error = $state<string | null>(null);
	let opening = $state<string | null>(null);

	onMount(async () => {
		try { pack = await getPackDocument(packId); }
		catch (cause) { error = cause instanceof Error ? cause.message : 'Could not load canonical quiz content.'; }
	});

	async function edit(generationId: string): Promise<void> {
		opening = generationId;
		try {
			const lesson = await openComponentLectioBuilderLesson(generationId);
			await goto(`/builder/${encodeURIComponent(lesson.id)}`);
		} catch (cause) { error = cause instanceof Error ? cause.message : 'Could not open this lesson in Builder.'; }
		finally { opening = null; }
	}
</script>

<svelte:head><title>Quiz content · Lectio</title></svelte:head>

<main class="mx-auto max-w-4xl px-4 py-8">
	{#if error}<p class="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-900" role="alert">{error}</p>{/if}
	{#if pack}
		<header class="mb-6"><p class="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Canonical quiz content</p><h1 class="mt-1 text-3xl font-semibold">{pack.topic}</h1><p class="mt-1 text-muted-foreground">Quiz items are part of each LessonDocument and are edited in Builder.</p></header>
		<div class="grid gap-4">
			{#each pack.resources as resource (resource.resource_id)}
				<article class="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-border/60 bg-card p-5 shadow-sm"><div><h2 class="font-semibold">{resource.label}</h2><p class="mt-1 text-sm text-muted-foreground">{resource.document ? 'Lesson document ready' : 'Document not ready yet'}</p></div>{#if resource.document && resource.generation_id}<button type="button" class="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50" disabled={opening === resource.generation_id} onclick={() => void edit(resource.generation_id!)}>{opening === resource.generation_id ? 'Opening…' : 'Edit in Builder'}</button>{/if}</article>
			{/each}
		</div>
	{:else if !error}<p class="rounded-xl border border-border/60 bg-card p-5 text-muted-foreground" role="status">Loading canonical quiz content…</p>{/if}
</main>
