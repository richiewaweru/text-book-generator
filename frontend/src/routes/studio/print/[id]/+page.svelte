<!-- Step 4: Readable V3 print — field-safe extraction, no diagnostic wrapper in PDF. -->
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
	let subject = $state('');

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
				subject?: string;
			};

			const rawSections = Array.isArray(data.sections) ? data.sections : [];
			sectionCount = rawSections.length;
			templateId = typeof data.template_id === 'string' ? data.template_id : 'missing';
			subject = typeof data.subject === 'string' ? data.subject.trim() : '';
			sections = mapPackSectionsToCanvas(rawSections);
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Failed to load print view.';
		} finally {
			complete = true;
		}
	});
</script>

<svelte:head>
	<title>{subject ? `${subject} — print` : 'Lesson print'}</title>
</svelte:head>

<div
	data-generation-complete={complete ? 'true' : 'false'}
	data-print-route="studio-print-readable"
	data-fetch-status={fetchStatus}
	data-section-count={sectionCount}
	data-template-id={templateId}
	data-generation-id={generationId}
>
	{#if complete && loadError}
		<p class="p-4 text-sm text-destructive">{loadError}</p>
	{:else if complete && !loadError}
		<V3PrintView {sections} {subject} />
	{/if}
</div>
