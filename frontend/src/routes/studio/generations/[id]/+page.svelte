<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';

	import { downloadV3GenerationPdf, fetchV3Document, getV3GenerationDetail } from '$lib/api/v3';
	import { coerceV3DocumentToPack } from '$lib/studio/v3-document';
	import { getBookletExportPolicy, isBookletStatus } from '$lib/studio/v3-booklet';
	import V3BookletPackView from '$lib/components/studio/V3BookletPackView.svelte';
	import type { BookletStatus, V3DraftPack, V3GenerationDetail } from '$lib/types/v3';

	const generationId = $derived(page.params.id ?? '');

	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let detail = $state<V3GenerationDetail | null>(null);
	let pack = $state<V3DraftPack | null>(null);
	let pdfLoading = $state(false);
	let pdfError = $state<string | null>(null);

	const resolvedStatus = $derived.by<BookletStatus>(() => {
		if (pack?.status) return pack.status;
		if (detail && isBookletStatus(detail.booklet_status)) {
			return detail.booklet_status;
		}
		return 'streaming_preview';
	});
	const exportPolicy = $derived(getBookletExportPolicy(resolvedStatus));

	async function loadGeneration(id: string): Promise<void> {
		loading = true;
		loadError = null;
		detail = null;
		pack = null;
		try {
			const [nextDetail, document] = await Promise.all([
				getV3GenerationDetail(id),
				fetchV3Document(id)
			]);
			detail = nextDetail;
			const nextPack = coerceV3DocumentToPack(id, document, {
				templateId: nextDetail.template_id,
				fallbackStatus: isBookletStatus(nextDetail.booklet_status)
					? nextDetail.booklet_status
					: 'draft_needs_review'
			});
			if (!nextPack) {
				throw new Error('Document is not renderable yet.');
			}
			pack = nextPack;
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Failed to load V3 generation.';
		} finally {
			loading = false;
		}
	}

	async function handleDownloadPdf() {
		if (!generationId) return;
		if (!exportPolicy.enabled) {
			pdfError = 'PDF export is unavailable for this booklet status.';
			return;
		}
		pdfLoading = true;
		pdfError = null;
		try {
			await downloadV3GenerationPdf(generationId, {
				school_name: '-',
				teacher_name: '-',
				include_toc: false,
				include_answers: true
			});
		} catch (err) {
			pdfError = err instanceof Error ? err.message : 'Failed to export PDF.';
		} finally {
			pdfLoading = false;
		}
	}

	onMount(() => {
		if (!generationId) {
			loading = false;
			loadError = 'Generation id is missing.';
			return;
		}
		void loadGeneration(generationId);
	});
</script>

<div class="mx-auto w-full max-w-5xl px-4 py-6">
	{#if loading}
		<p class="text-sm text-muted-foreground">Loading V3 generation...</p>
	{:else if loadError}
		<p class="text-sm text-destructive" role="alert">{loadError}</p>
	{:else if pack}
		<div class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-card p-4">
			<div>
				<p class="text-xs uppercase tracking-wide text-muted-foreground">V3 generation</p>
				<h1 class="text-lg font-semibold">{detail?.title ?? detail?.subject ?? generationId}</h1>
				<p class="text-sm text-muted-foreground">
					Status: {pack.status} - Sections: {pack.sections.length}
				</p>
			</div>
			<button
				type="button"
				class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
				onclick={handleDownloadPdf}
				disabled={pdfLoading || !exportPolicy.enabled}
			>
				{pdfLoading ? 'Generating PDF...' : exportPolicy.label}
			</button>
		</div>
		{#if pdfError}
			<p class="mb-4 text-sm text-destructive" role="alert">{pdfError}</p>
		{/if}
		<V3BookletPackView pack={pack} status={pack.status} issues={pack.booklet_issues} />
	{:else}
		<p class="text-sm text-muted-foreground">No renderable V3 booklet was found.</p>
	{/if}
</div>
