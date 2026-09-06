<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { getPackDocument, getPackStatus, type CanonicalPackDocumentResponse } from '$lib/api/learning-pack';
	import { openComponentLectioBuilderLesson } from '$lib/builder/api/lesson-crud';

	const packId = $derived(page.params.pack_id ?? '');
	let status = $state<Awaited<ReturnType<typeof getPackStatus>> | null>(null);
	let pack = $state<CanonicalPackDocumentResponse | null>(null);
	let error = $state<string | null>(null);
	let openingGenerationId = $state<string | null>(null);
	let timer: ReturnType<typeof setInterval> | null = null;

	async function refresh(): Promise<void> {
		try {
			const [nextStatus, nextPack] = await Promise.all([getPackStatus(packId), getPackDocument(packId)]);
			status = nextStatus;
			pack = nextPack;
			error = null;
			if (nextStatus.status === 'complete' || nextStatus.status === 'failed') {
				if (timer) clearInterval(timer);
				timer = null;
			}
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not load this pack.';
		}
	}

	async function openInBuilder(generationId: string): Promise<void> {
		openingGenerationId = generationId;
		try {
			const lesson = await openComponentLectioBuilderLesson(generationId);
			await goto(`/builder/${encodeURIComponent(lesson.id)}`);
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not open this lesson in Builder.';
		} finally {
			openingGenerationId = null;
		}
	}

	onMount(() => {
		void refresh();
		timer = setInterval(() => void refresh(), 4000);
	});
	onDestroy(() => { if (timer) clearInterval(timer); });
</script>

<svelte:head><title>{pack ? `${pack.topic} · Learning pack` : 'Learning pack · Lectio'}</title></svelte:head>

<section class="mx-auto grid max-w-5xl gap-6 px-4 py-8">
	{#if error}<p class="rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">{error}</p>{/if}
	{#if pack && status}
		<header class="rounded-3xl border border-border/60 bg-card p-6 shadow-sm">
			<p class="text-sm font-semibold uppercase tracking-[0.22em] text-muted-foreground">Canonical learning pack</p>
			<h1 class="mt-2 text-3xl font-semibold tracking-tight">{pack.topic}</h1>
			<p class="mt-1 text-muted-foreground">{pack.subject} · {status.completed_count} of {status.resource_count} resources ready</p>
		</header>
		<div class="grid gap-4 md:grid-cols-2">
			{#each pack.resources as resource (resource.resource_id)}
				<article class="grid content-start gap-3 rounded-3xl border border-border/60 bg-card p-5 shadow-sm">
					<div class="flex items-start justify-between gap-3"><h2 class="text-xl font-semibold">{resource.label}</h2><span class="rounded-full bg-muted px-2.5 py-1 text-xs font-bold uppercase tracking-wide">{resource.status}</span></div>
					{#if resource.document && resource.generation_id}
						<p class="text-sm text-muted-foreground">Canonical lesson document ready for editing.</p>
						<button type="button" class="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50" disabled={openingGenerationId === resource.generation_id} onclick={() => void openInBuilder(resource.generation_id!)}>{openingGenerationId === resource.generation_id ? 'Opening…' : 'Open in Builder'}</button>
					{:else}
						<p class="text-sm text-muted-foreground">This resource is still being prepared.</p>
					{/if}
				</article>
			{/each}
		</div>
	{:else if !error}
		<p class="rounded-2xl border border-border/60 bg-card p-5 text-muted-foreground" role="status">Loading canonical pack…</p>
	{/if}
</section>
