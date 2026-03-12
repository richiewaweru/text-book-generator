<script lang="ts">
	import { page } from '$app/state';
	import TextbookViewer from '$lib/components/TextbookViewer.svelte';
	import { fetchTextbookHtml, getGenerationDetail, getGenerationStatus } from '$lib/api/client';

	const textbookId = $derived(page.params.id);

	let html = $state('');
	let loading = $state(true);
	let error: string | null = $state(null);

	async function ensureCompletedGeneration(id: string): Promise<void> {
		try {
			const status = await getGenerationStatus(id);
			if (status.status === 'completed') {
				return;
			}
			if (status.status === 'failed') {
				throw new Error(status.error ?? 'Generation failed.');
			}
		} catch {
			// Fall back to the persisted generation record for historical loads.
		}

		const detail = await getGenerationDetail(id);
		if (detail.status === 'completed') {
			return;
		}
		if (detail.status === 'failed') {
			throw new Error(detail.error ?? 'Generation failed.');
		}
		throw new Error(`Textbook status: ${detail.status}`);
	}

	async function loadTextbook(id: string) {
		loading = true;
		error = null;

		try {
			await ensureCompletedGeneration(id);
			html = await fetchTextbookHtml(id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load textbook.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (textbookId) {
			loadTextbook(textbookId);
		}
	});
</script>

<div class="page-shell">
	<h1>Textbook: {textbookId}</h1>

	{#if error}
		<p class="error"><strong>Error:</strong> {error}</p>
	{:else if loading}
		<p class="loading">Loading textbook...</p>
	{:else}
		<TextbookViewer {html} />
	{/if}
</div>

<style>
	.page-shell {
		display: grid;
		gap: 1rem;
	}

	h1 {
		margin: 0;
		font-size: 1.4rem;
	}

	.loading {
		color: #888;
	}

	.error {
		background: #2a1515;
		border: 1px solid #5a2020;
		border-radius: 8px;
		padding: 1rem;
		color: #e57373;
	}
</style>
