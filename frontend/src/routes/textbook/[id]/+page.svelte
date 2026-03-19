<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { SectionContent } from 'lectio';
	import LectioDocumentView from '$lib/components/LectioDocumentView.svelte';
	import {
		buildGenerationEventsUrl,
		enhanceGeneration,
		getGenerationDetail,
		getGenerationDocument
	} from '$lib/api/client';
	import { friendlyGenerationErrorMessage } from '$lib/generation/error-messages';
	import type {
		ErrorEvent,
		GenerationDetail,
		GenerationDocument,
		QCCompleteEvent,
		SectionReadyEvent
	} from '$lib/types';

	const generationId = $derived(page.params.id);

	let detail = $state<GenerationDetail | null>(null);
	let document = $state<GenerationDocument | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let enhancing = $state(false);
	let eventSource = $state<EventSource | null>(null);
	let streamState = $state<'idle' | 'connected' | 'reconnecting' | 'complete'>('idle');
	let plannedSections = $state<number | null>(null);
	let qcSummary = $state<{ passed: number; total: number } | null>(null);

	function closeStream() {
		eventSource?.close();
		eventSource = null;
	}

	function upsertSection(nextSection: SectionContent) {
		if (!document) {
			return;
		}
		const sections = [...document.sections];
		const existingIndex = sections.findIndex((section) => section.section_id === nextSection.section_id);
		if (existingIndex >= 0) {
			sections[existingIndex] = nextSection;
		} else {
			sections.push(nextSection);
		}
		document = { ...document, sections, status: 'running', updated_at: new Date().toISOString() };
	}

	async function refresh(id: string) {
		detail = await getGenerationDetail(id);
		document = await getGenerationDocument(id);
	}

	function connectStream(id: string) {
		closeStream();
		const source = new EventSource(buildGenerationEventsUrl(id));
		eventSource = source;
		streamState = 'connected';

		source.addEventListener('pipeline_start', (event) => {
			const payload = JSON.parse((event as MessageEvent).data) as { section_count: number };
			plannedSections = payload.section_count;
		});

		source.addEventListener('section_ready', (event) => {
			const payload = JSON.parse((event as MessageEvent).data) as SectionReadyEvent;
			plannedSections = payload.total_sections;
			upsertSection(payload.section);
		});

		source.addEventListener('qc_complete', (event) => {
			const payload = JSON.parse((event as MessageEvent).data) as QCCompleteEvent;
			qcSummary = { passed: payload.passed, total: payload.total };
		});

		source.addEventListener('complete', async () => {
			streamState = 'complete';
			closeStream();
			await refresh(id);
		});

		source.addEventListener('error', async (event) => {
			if (event instanceof MessageEvent) {
				const payload = JSON.parse(event.data) as ErrorEvent;
				error = payload.message;
				streamState = 'complete';
				closeStream();
				await refresh(id);
				return;
			}
			streamState = 'reconnecting';
		});
	}

	async function loadGeneration(id: string) {
		loading = true;
		error = null;
		qcSummary = null;
		plannedSections = null;
		closeStream();

		try {
			await refresh(id);
			plannedSections = document?.sections.length ?? null;

			if (detail?.status === 'failed') {
				error = friendlyGenerationErrorMessage(detail.error, detail.error_type, detail.error_code);
				return;
			}

			if (detail?.status === 'pending' || detail?.status === 'running') {
				connectStream(id);
			} else {
				streamState = 'complete';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load generation.';
		} finally {
			loading = false;
		}
	}

	async function handleEnhance() {
		if (!generationId) {
			return;
		}

		enhancing = true;
		error = null;

		try {
			const accepted = await enhanceGeneration(generationId, { mode: 'balanced' });
			goto(`/textbook/${accepted.generation_id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to enhance draft.';
		} finally {
			enhancing = false;
		}
	}

	$effect(() => {
		if (!generationId) {
			return;
		}
		void loadGeneration(generationId);
		return () => {
			closeStream();
		};
	});
</script>

<div class="page-shell">
	<div class="header">
		<div>
			<p class="eyebrow">Generation</p>
			<h1>{detail?.subject ?? generationId}</h1>
			{#if detail}
				<div class="meta">
					<span class="status status-{detail.status}">{detail.status}</span>
					<span class="mode">{detail.mode.toUpperCase()}</span>
					<span>{detail.resolved_template_id ?? detail.requested_template_id}</span>
					<span>{detail.resolved_preset_id ?? detail.requested_preset_id}</span>
				</div>
			{/if}
		</div>
		{#if detail?.mode === 'draft' && detail.status === 'completed'}
			<button class="enhance-button" onclick={handleEnhance} disabled={enhancing}>
				{enhancing ? 'Enhancing...' : 'Enhance Draft'}
			</button>
		{/if}
	</div>

	{#if plannedSections !== null}
		<div class="status-panel">
			<p>
				Sections ready: {document?.sections.length ?? 0} / {plannedSections}
			</p>
			<p>Stream: {streamState}</p>
			{#if qcSummary}
				<p>QC: {qcSummary.passed} / {qcSummary.total} passing</p>
			{/if}
		</div>
	{/if}

	{#if detail?.mode === 'draft'}
		<p class="draft-note">
			Draft mode is the fast seedable pass. Use Enhance Draft to keep the section structure and let
			the pipeline rework it in balanced mode.
		</p>
	{/if}

	{#if error}
		<div class="error"><strong>Error:</strong> {error}</div>
	{:else if loading}
		<p>Loading generation...</p>
	{:else if document}
		<LectioDocumentView {document} />
	{:else}
		<p>No document is available yet.</p>
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

	.eyebrow {
		margin: 0 0 0.3rem 0;
		font-size: 0.78rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h1 {
		margin: 0;
		font-size: 1.6rem;
	}

	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem;
		margin-top: 0.5rem;
		color: #5d554a;
	}

	.status,
	.mode {
		padding: 0.2rem 0.55rem;
		border-radius: 999px;
		font-size: 0.76rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.status-pending,
	.status-running {
		background: rgba(54, 101, 130, 0.12);
		color: #28516b;
	}

	.status-completed {
		background: rgba(61, 120, 73, 0.13);
		color: #276135;
	}

	.status-failed {
		background: rgba(148, 66, 46, 0.12);
		color: #8d3a26;
	}

	.mode {
		background: rgba(36, 52, 63, 0.08);
		color: #24343f;
	}

	.status-panel,
	.draft-note,
	.error {
		padding: 1rem;
		border-radius: 18px;
		background: rgba(255, 251, 244, 0.84);
		border: 1px solid rgba(36, 52, 63, 0.1);
	}

	.enhance-button {
		border-radius: 999px;
		border: none;
		background: linear-gradient(135deg, #1f3d52, #325d78);
		color: #fff;
		padding: 0.7rem 1rem;
		cursor: pointer;
		font: inherit;
		font-weight: 600;
	}

	.error {
		border-color: rgba(148, 66, 46, 0.18);
		background: rgba(255, 242, 238, 0.9);
		color: #7d3524;
	}
</style>
