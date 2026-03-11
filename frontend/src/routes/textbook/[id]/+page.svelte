<script lang="ts">
	import { page } from '$app/state';
	import TextbookViewer from '$lib/components/TextbookViewer.svelte';
	import { getGenerationStatus } from '$lib/api/client';

	const textbookId = $derived(page.params.id);

	let html = $state('<p>Loading textbook...</p>');
	let error: string | null = $state(null);

	async function loadTextbook(id: string) {
		try {
			const status = await getGenerationStatus(id);
			if (status.status === 'completed' && status.result?.output_path) {
				const API_BASE = 'http://localhost:8000';
				const response = await fetch(
					`${API_BASE}/api/v1/textbook/${encodeURIComponent(status.result.output_path)}`
				);
				if (response.ok) {
					html = await response.text();
				} else {
					error = 'Failed to load textbook content.';
				}
			} else if (status.status === 'failed') {
				error = status.error ?? 'Generation failed.';
			} else {
				error = `Textbook status: ${status.status}`;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load textbook.';
		}
	}

	$effect(() => {
		if (textbookId) {
			loadTextbook(textbookId);
		}
	});
</script>

<h1>Textbook: {textbookId}</h1>

{#if error}
	<p class="error"><strong>Error:</strong> {error}</p>
{:else}
	<TextbookViewer {html} />
{/if}
