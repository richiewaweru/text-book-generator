<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import GenerationProgress from '$lib/components/GenerationProgress.svelte';
	import TextbookViewer from '$lib/components/TextbookViewer.svelte';
	import {
		enhanceGeneration,
		fetchTextbookHtml,
		getGenerationDetail,
		getGenerationStatus,
		pollUntilDone
	} from '$lib/api/client';
	import type { GenerationDetail, GenerationStatus } from '$lib/types';

	const textbookId = $derived(page.params.id);

	let detail = $state<GenerationDetail | null>(null);
	let html = $state('');
	let loading = $state(true);
	let error: string | null = $state(null);
	let enhancing = $state(false);
	let enhanceStatus = $state<GenerationStatus | null>(null);

	async function ensureCompletedGeneration(id: string): Promise<GenerationDetail> {
		try {
			const status = await getGenerationStatus(id);
			if (status.status === 'completed') {
				return (await getGenerationDetail(id)) as GenerationDetail;
			}
			if (status.status === 'failed') {
				throw new Error(status.error ?? 'Generation failed.');
			}
		} catch {
			// Fall back to the persisted generation record for historical loads.
		}

		const generationDetail = await getGenerationDetail(id);
		if (generationDetail.status === 'completed') {
			return generationDetail;
		}
		if (generationDetail.status === 'failed') {
			throw new Error(generationDetail.error ?? 'Generation failed.');
		}
		throw new Error(`Textbook status: ${generationDetail.status}`);
	}

	async function loadTextbook(id: string) {
		loading = true;
		error = null;

		try {
			detail = await ensureCompletedGeneration(id);
			html = await fetchTextbookHtml(id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load textbook.';
		} finally {
			loading = false;
		}
	}

	async function handleEnhance() {
		if (!textbookId) {
			return;
		}

		enhancing = true;
		enhanceStatus = null;
		error = null;

		try {
			const { generation_id } = await enhanceGeneration(textbookId, { target_mode: 'balanced' });
			const finalStatus = await pollUntilDone(generation_id, (status) => {
				enhanceStatus = status;
			});
			if (finalStatus.status === 'completed') {
				goto(`/textbook/${generation_id}`);
			} else if (finalStatus.status === 'failed') {
				throw new Error(finalStatus.error ?? 'Draft enhancement failed.');
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to enhance draft.';
		} finally {
			enhancing = false;
		}
	}

	function modeLabel(mode: string | null | undefined): string {
		return (mode ?? '').toUpperCase();
	}

	$effect(() => {
		if (textbookId) {
			loadTextbook(textbookId);
		}
	});
</script>

<div class="page-shell">
	<div class="header">
		<div>
			<h1>Textbook: {textbookId}</h1>
			{#if detail}
				<div class="meta">
					<span class="mode-badge mode-{detail.mode}">{modeLabel(detail.mode)}</span>
					{#if detail.source_generation_id}
						<span class="linked">Enhanced from {detail.source_generation_id}</span>
					{/if}
				</div>
			{/if}
		</div>
		{#if detail?.mode === 'draft'}
			<button class="enhance-button" onclick={handleEnhance} disabled={enhancing}>
				{enhancing ? 'Enhancing draft...' : 'Enhance draft'}
			</button>
		{/if}
	</div>

	{#if enhanceStatus}
		<GenerationProgress status={enhanceStatus} />
	{/if}

	{#if detail?.mode === 'draft'}
		<p class="draft-note">
			This is a draft build. It keeps the fast survey structure and skips the final document review.
		</p>
	{/if}

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

	.header {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	h1 {
		margin: 0;
		font-size: 1.4rem;
	}

	.mode-badge {
		padding: 0.2rem 0.5rem;
		border-radius: 999px;
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.mode-draft {
		background: #2f2612;
		color: #f1c96c;
	}

	.mode-balanced {
		background: #173221;
		color: #86d39e;
	}

	.mode-strict {
		background: #2a1d3b;
		color: #caa2ff;
	}

	.linked,
	.loading,
	.draft-note {
		color: #888;
	}

	.enhance-button {
		background: #173221;
		border: 1px solid #86d39e;
		color: #86d39e;
		border-radius: 6px;
		padding: 0.6rem 0.9rem;
		cursor: pointer;
	}

	.enhance-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error {
		background: #2a1515;
		border: 1px solid #5a2020;
		border-radius: 8px;
		padding: 1rem;
		color: #e57373;
	}
</style>
