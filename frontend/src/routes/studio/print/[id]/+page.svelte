<!-- Step 1: Fetch diagnostic print page — proves V3 document API from Playwright before restoring full print UI. -->
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

			sectionCount = Array.isArray(data.sections) ? data.sections.length : 0;
			templateId = typeof data.template_id === 'string' ? data.template_id : 'missing';
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Failed to load print view.';
		} finally {
			complete = true;
		}
	});
</script>

<svelte:head>
	<title>Studio print fetch test</title>
</svelte:head>

<div
	data-generation-complete={complete ? 'true' : 'false'}
	data-print-route="studio-print-fetch-test"
	data-fetch-status={fetchStatus}
	data-section-count={sectionCount}
	data-generation-id={generationId}
>
	<h1>V3 Print Fetch Test</h1>
	<p>Generation ID: {generationId}</p>
	<p>Fetch status: {fetchStatus}</p>
	<p>Section count: {sectionCount}</p>
	<p>Template ID: {templateId}</p>
	<p>Load error: {loadError ?? 'none'}</p>
</div>
