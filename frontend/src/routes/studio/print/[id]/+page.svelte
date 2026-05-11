<!-- Step 2: Fetch + plain section titles for PDF print — no V3Canvas / Lectio. -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { buildApiUrl } from '$lib/api/client';

	const generationId = $derived(page.params.id);
	const token = $derived(page.url.searchParams.get('token'));

	let complete = $state(false);
	let fetchStatus = $state('not-started');
	let sectionCount = $state(0);
	let templateId = $state('none');
	let loadError = $state<string | null>(null);
	let sectionTitles = $state<string[]>([]);

	function extractSectionTitle(section: unknown, index: number): string {
		if (!section || typeof section !== 'object') {
			return `Section ${index + 1}`;
		}
		const s = section as Record<string, unknown>;
		const header = s.header;
		if (header && typeof header === 'object') {
			const h = header as Record<string, unknown>;
			if (typeof h.title === 'string' && h.title.trim()) {
				return h.title.trim();
			}
		}
		if (typeof s.section_id === 'string' && s.section_id) {
			return s.section_id;
		}
		return `Section ${index + 1}`;
	}

	onMount(async () => {
		try {
			if (!generationId) {
				loadError = 'Missing generation id.';
				return;
			}

			fetchStatus = 'fetching';

			const endpoint = buildApiUrl(
				`/api/v1/v3/generations/${encodeURIComponent(generationId)}/document`
			);

			const headers: Record<string, string> = {};
			if (token) headers.Authorization = `Bearer ${token}`;

			const res = await fetch(endpoint, { headers });
			fetchStatus = `response-${res.status}`;

			if (!res.ok) {
				loadError = `Document unavailable for print (${res.status}).`;
				return;
			}

			const data = (await res.json()) as {
				sections?: unknown[];
				template_id?: string;
			};

			const sections = Array.isArray(data.sections) ? data.sections : [];
			sectionCount = sections.length;
			templateId = typeof data.template_id === 'string' ? data.template_id : 'missing';
			sectionTitles = sections.map((sec, i) => extractSectionTitle(sec, i));
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Failed to load print view.';
		} finally {
			complete = true;
		}
	});
</script>

<svelte:head>
	<title>Studio print section titles</title>
</svelte:head>

<div
	data-generation-complete={complete ? 'true' : 'false'}
	data-print-route="studio-print-section-titles"
	data-fetch-status={fetchStatus}
	data-section-count={sectionCount}
	data-generation-id={generationId}
>
	<h1>V3 Section Title Test</h1>
	<p>Generation ID: {generationId}</p>
	<p>Fetch status: {fetchStatus}</p>
	<p>Section count: {sectionCount}</p>
	<p>Template ID: {templateId}</p>
	<p>Load error: {loadError ?? 'none'}</p>

	{#if sectionTitles.length > 0}
		<ol class="section-title-list">
			{#each sectionTitles as title}
				<li>{title}</li>
			{/each}
		</ol>
	{/if}
</div>

<style>
	.section-title-list {
		margin: 1rem 0 0;
		padding-left: 1.5rem;
		font-size: 1rem;
		line-height: 1.5;
	}
</style>
