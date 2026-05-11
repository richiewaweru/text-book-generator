<!-- Step 3A: Fetch + V3PrintView JSON payload dump for PDF — no V3Canvas / Lectio. -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { buildApiUrl } from '$lib/api/client';
	import V3PrintView from '$lib/components/studio/V3PrintView.svelte';
	import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
	import type { CanvasSection } from '$lib/types/v3';

	const generationId = $derived(page.params.id);
	const token = $derived(page.url.searchParams.get('token'));

	let complete = $state(false);
	let fetchStatus = $state('not-started');
	let sectionCount = $state(0);
	let templateId = $state('none');
	let loadError = $state<string | null>(null);
	let sections = $state<CanvasSection[]>([]);

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

			const rawSections = Array.isArray(data.sections) ? data.sections : [];
			sectionCount = rawSections.length;
			templateId = typeof data.template_id === 'string' ? data.template_id : 'missing';
			sections = mapPackSectionsToCanvas(rawSections);
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Failed to load print view.';
		} finally {
			complete = true;
		}
	});
</script>

<svelte:head>
	<title>Studio print payload test</title>
</svelte:head>

<div
	data-generation-complete={complete ? 'true' : 'false'}
	data-print-route="studio-print-payload-test"
	data-fetch-status={fetchStatus}
	data-section-count={sectionCount}
	data-generation-id={generationId}
>
	<h1>V3 Print Payload Test Wrapper</h1>
	<p>Fetch status: {fetchStatus}</p>
	<p>Section count: {sectionCount}</p>
	<p>Template ID: {templateId}</p>
	<p>Load error: {loadError ?? 'none'}</p>

	{#if complete && !loadError}
		<V3PrintView {sections} />
	{/if}
</div>
