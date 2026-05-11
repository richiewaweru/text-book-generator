<!-- V3 studio print: default Lectio template render; renderer=safe for flat debug; renderer=canvas-test for canvas diagnostics. -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { providePrintMode } from 'lectio';
	import '$lib/styles/print.css';
	import { buildApiUrl } from '$lib/api/client';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';
	import V3LectioPrintDocumentView from '$lib/components/studio/V3LectioPrintDocumentView.svelte';
	import V3PrintView from '$lib/components/studio/V3PrintView.svelte';
	import { adaptV3PackToLectioDocument, type V3PackDocument } from '$lib/studio/v3-pack-to-lectio-document';
	import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
	import type { GenerationDocument } from '$lib/types';
	import type { CanvasSection } from '$lib/types/v3';

	const generationId = $derived(page.params.id);
	const token = $derived(page.url.searchParams.get('token'));
	const renderer = $derived(page.url.searchParams.get('renderer') ?? 'lectio');
	const debugPrint = $derived(page.url.searchParams.get('debugPrint') === 'true');
	const showPrintDiagnostics = $derived(debugPrint || renderer === 'canvas-test');

	providePrintMode(() => page.url.searchParams.get('print') === 'true');

	let complete = $state(false);
	let fetchStatus = $state('not-started');
	let sectionCount = $state(0);
	let templateId = $state('none');
	let loadError = $state<string | null>(null);
	let rawSections = $state<unknown[]>([]);
	let lectioDocument = $state<GenerationDocument | null>(null);
	let subject = $state('');

	const sections = $derived<CanvasSection[]>(
		renderer === 'safe' || renderer === 'canvas-test'
			? mapPackSectionsToCanvas(rawSections)
			: []
	);

	const templateIdForCanvas = $derived(
		templateId && templateId !== 'missing' && templateId !== 'none' ? templateId : 'guided-concept-path'
	);

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

			const data = (await res.json()) as V3PackDocument;

			const list = Array.isArray(data.sections) ? data.sections : [];
			rawSections = list;
			sectionCount = list.length;
			templateId = typeof data.template_id === 'string' ? data.template_id : 'missing';
			subject = typeof data.subject === 'string' ? data.subject.trim() : '';

			try {
				lectioDocument = adaptV3PackToLectioDocument(data, { routeGenerationId: generationId });
			} catch {
				lectioDocument = null;
			}
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
	data-renderer={renderer}
	data-fetch-status={fetchStatus}
	data-section-count={sectionCount}
	data-template-id={templateId}
	data-generation-id={generationId}
>
	{#if complete && loadError}
		<p class="print-error">{loadError}</p>
	{:else if complete && !loadError}
		{#if showPrintDiagnostics}
			<div class="print-diagnostics">
				<p><span class="print-diagnostics-label">Renderer:</span> {renderer}</p>
				<p><span class="print-diagnostics-label">Fetch status:</span> {fetchStatus}</p>
				<p><span class="print-diagnostics-label">Section count:</span> {sectionCount}</p>
				<p><span class="print-diagnostics-label">Template ID:</span> {templateId}</p>
				<p><span class="print-diagnostics-label">Load error:</span> {loadError ?? 'none'}</p>
			</div>
		{/if}

		{#if renderer === 'canvas-test'}
			<V3Canvas {sections} stage="complete" templateId={templateIdForCanvas} />
		{:else if renderer === 'safe'}
			<V3PrintView {sections} {subject} />
		{:else if lectioDocument}
			<V3LectioPrintDocumentView document={lectioDocument} />
		{:else}
			<p class="print-error">Unable to adapt V3 pack for print.</p>
		{/if}
	{/if}
</div>

<style>
	.print-error {
		padding: 1rem;
		font-size: 0.875rem;
		color: #b91c1c;
	}

	.print-diagnostics {
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid #ccc;
		font-size: 0.75rem;
		line-height: 1.4;
		color: #333;
	}

	.print-diagnostics p {
		margin: 0.15rem 0;
	}

	.print-diagnostics-label {
		font-weight: 600;
		margin-right: 0.35rem;
	}
</style>
