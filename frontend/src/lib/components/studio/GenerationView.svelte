<script lang="ts">
	import { onDestroy } from 'svelte';

	import {
		buildGenerationEventsUrl,
		getGenerationDetail,
		getGenerationDocument
	} from '$lib/api/client';
	import LectioDocumentView from '$lib/components/LectioDocumentView.svelte';
	import { friendlyGenerationErrorMessage } from '$lib/generation/error-messages';
	import {
		applySectionFailed,
		applySectionReady,
		applySectionStarted,
		buildSectionSlots,
		normalizeDocument
	} from '$lib/generation/viewer-state';
	import { setGenerationBanner, setGenerationDocument } from '$lib/stores/studio';
	import type {
		ErrorEvent,
		GenerationAccepted,
		GenerationDetail,
		GenerationDocument,
		ProgressUpdateEvent,
		QCCompleteEvent,
		SectionFailedEvent,
		SectionReadyEvent,
		SectionStartedEvent
	} from '$lib/types';

	interface Props {
		accepted: GenerationAccepted;
		onReset: () => void;
	}

	let { accepted, onReset }: Props = $props();

	let detail = $state<GenerationDetail | null>(null);
	let document = $state<GenerationDocument | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let streamState = $state<'idle' | 'connected' | 'reconnecting' | 'complete'>('idle');
	let plannedSections = $state<number | null>(null);
	let qcSummary = $state<{ passed: number; total: number } | null>(null);
	let progressUpdate = $state<ProgressUpdateEvent | null>(null);
	let viewerWarning = $state<string | null>(null);
	let eventSource: EventSource | null = null;
	let streamClosedTerminally = false;
	let streamErrorRecoveryAttempted = false;

	const generationId = $derived(accepted.generation_id);
	const sectionSlots = $derived(buildSectionSlots(document, plannedSections));
	const readySectionCount = $derived(
		sectionSlots.filter((slot) => slot.status === 'ready').length
	);
	const failedSectionCount = $derived(
		sectionSlots.filter((slot) => slot.status === 'failed').length
	);
	const streamLabel = $derived(
		detail?.status === 'completed'
			? detail.quality_passed === false
				? 'completed with QC issues'
				: 'complete'
			: detail?.status === 'failed'
				? 'failed'
				: progressUpdate?.label ?? streamState
	);

	function closeStream(source: EventSource | null = eventSource) {
		source?.close();
		if (source === eventSource) {
			eventSource = null;
		}
	}

	function syncDocument(nextDocument: GenerationDocument) {
		const normalized = normalizeDocument(nextDocument);
		document = normalized;
		setGenerationDocument(normalized);
	}

	function applyGenerationSnapshot(nextDetail: GenerationDetail, nextDocument: GenerationDocument) {
		const normalizedDocument = normalizeDocument(nextDocument);
		const manifestCount = normalizedDocument.section_manifest.length;
		const sectionCount = normalizedDocument.sections.length;

		detail = nextDetail;
		document = normalizedDocument;
		setGenerationDocument(normalizedDocument);
		plannedSections =
			nextDetail.section_count ??
			(manifestCount > 0 ? manifestCount : sectionCount > 0 ? sectionCount : null);
		qcSummary = normalizedDocument.qc_reports.length
			? {
					passed: normalizedDocument.qc_reports.filter((report) => report.passed).length,
					total: normalizedDocument.qc_reports.length
				}
			: null;
	}

	async function refresh(id: string) {
		const [nextDetail, nextDocument] = await Promise.all([
			getGenerationDetail(id),
			getGenerationDocument(id)
		]);
		applyGenerationSnapshot(nextDetail, nextDocument);
	}

	async function finalizeStream(source: EventSource, id: string, nextError: string | null = null) {
		if (source !== eventSource) {
			return;
		}

		streamClosedTerminally = true;
		streamState = 'complete';
		setGenerationBanner(null);
		closeStream(source);
		await refresh(id);

		if (detail?.status === 'failed') {
			error = friendlyGenerationErrorMessage(detail.error, detail.error_type, detail.error_code);
			return;
		}

		if (nextError) {
			error = nextError;
		}
	}

	async function revalidateTerminalState(source: EventSource, id: string): Promise<boolean> {
		if (source !== eventSource || streamErrorRecoveryAttempted) {
			return false;
		}

		streamErrorRecoveryAttempted = true;
		try {
			await refresh(id);
		} catch {
			return false;
		}

		if (source !== eventSource) {
			return false;
		}

		if (detail?.status === 'completed' || detail?.status === 'failed') {
			streamClosedTerminally = true;
			streamState = 'complete';
			setGenerationBanner(null);
			closeStream(source);
			if (detail.status === 'failed') {
				error = friendlyGenerationErrorMessage(detail.error, detail.error_type, detail.error_code);
			}
			return true;
		}

		return false;
	}

	function connectStream(id: string) {
		closeStream();
		const source = new EventSource(buildGenerationEventsUrl(id));
		eventSource = source;
		streamClosedTerminally = false;
		streamErrorRecoveryAttempted = false;
		streamState = 'connected';
		setGenerationBanner('Live generation connected.');

		source.addEventListener('pipeline_start', (event) => {
			if (source !== eventSource) return;
			const payload = JSON.parse((event as MessageEvent).data) as { section_count: number };
			plannedSections = payload.section_count;
		});

		source.addEventListener('progress_update', (event) => {
			if (source !== eventSource) return;
			progressUpdate = JSON.parse((event as MessageEvent).data) as ProgressUpdateEvent;
		});

		source.addEventListener('section_started', (event) => {
			if (source !== eventSource || !document) return;
			const payload = JSON.parse((event as MessageEvent).data) as SectionStartedEvent;
			syncDocument(applySectionStarted(document, payload));
		});

		source.addEventListener('section_ready', (event) => {
			if (source !== eventSource || !document) return;
			const payload = JSON.parse((event as MessageEvent).data) as SectionReadyEvent;
			plannedSections = payload.total_sections;
			const result = applySectionReady(document, payload);
			syncDocument(result.document);
			if (result.warning) {
				viewerWarning = result.warning.message;
			}
		});

		source.addEventListener('section_failed', (event) => {
			if (source !== eventSource || !document) return;
			const payload = JSON.parse((event as MessageEvent).data) as SectionFailedEvent;
			syncDocument(applySectionFailed(document, payload));
		});

		source.addEventListener('qc_complete', (event) => {
			if (source !== eventSource) return;
			const payload = JSON.parse((event as MessageEvent).data) as QCCompleteEvent;
			qcSummary = { passed: payload.passed, total: payload.total };
		});

		source.addEventListener('complete', async () => {
			await finalizeStream(source, id);
		});

		source.addEventListener('error', async (event) => {
			if (event instanceof MessageEvent) {
				const payload = JSON.parse(event.data) as ErrorEvent;
				await finalizeStream(source, id, payload.message);
				return;
			}

			if (source !== eventSource) {
				return;
			}

			if (streamClosedTerminally || detail?.status === 'completed' || detail?.status === 'failed') {
				streamState = 'complete';
				setGenerationBanner(null);
				closeStream(source);
				return;
			}

			if (await revalidateTerminalState(source, id)) {
				return;
			}

			streamState = 'reconnecting';
			setGenerationBanner('Reconnecting to the live generation stream...');
		});
	}

	async function loadGeneration(id: string) {
		loading = true;
		error = null;
		qcSummary = null;
		plannedSections = null;
		progressUpdate = null;
		viewerWarning = null;
		streamClosedTerminally = false;
		streamErrorRecoveryAttempted = false;
		setGenerationBanner(null);
		closeStream();

		try {
			await refresh(id);

			if (detail?.status === 'failed') {
				error = friendlyGenerationErrorMessage(detail.error, detail.error_type, detail.error_code);
				streamState = 'complete';
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

	$effect(() => {
		if (!generationId) {
			return;
		}

		void loadGeneration(generationId);
		return () => {
			closeStream();
			setGenerationBanner(null);
		};
	});

	onDestroy(() => {
		closeStream();
		setGenerationBanner(null);
	});
</script>

<section class="generation-shell">
	<div class="generation-header">
		<div>
			<p class="eyebrow">Generating</p>
			<h2>Lesson in progress</h2>
			<p class="lede">
				The committed plan is now driving the live Lectio generation stream. Sections will appear
				here as soon as they are ready.
			</p>
		</div>
		<div class="header-actions">
			<a class="open-link" href={`/textbook/${generationId}`}>Open full lesson</a>
			<button class="secondary-button" type="button" onclick={onReset}>Create another lesson</button>
		</div>
	</div>

	<div class="status-grid">
		<div class="status-card">
			<span class="status-label">Status</span>
			<strong>{streamLabel}</strong>
		</div>
		<div class="status-card">
			<span class="status-label">Sections ready</span>
			<strong>{readySectionCount}{plannedSections ? ` / ${plannedSections}` : ''}</strong>
		</div>
		<div class="status-card">
			<span class="status-label">Failed sections</span>
			<strong>{failedSectionCount}</strong>
		</div>
		<div class="status-card">
			<span class="status-label">QC</span>
			<strong>{qcSummary ? `${qcSummary.passed} / ${qcSummary.total}` : 'Pending'}</strong>
		</div>
	</div>

	{#if viewerWarning}
		<p class="notice notice-warn">{viewerWarning}</p>
	{/if}

	{#if error}
		<p class="notice notice-error">{error}</p>
	{:else if loading}
		<div class="loading-panel" aria-busy="true">
			<div class="skeleton-line short"></div>
			<div class="skeleton-line"></div>
			<div class="skeleton-line"></div>
		</div>
	{:else if document}
		<LectioDocumentView {document} sectionSlots={sectionSlots} />
	{:else}
		<p class="notice">Waiting for the first generation update.</p>
	{/if}
</section>

<style>
	.generation-shell {
		display: grid;
		gap: 1rem;
	}

	.generation-header,
	.header-actions {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.eyebrow,
	.status-label {
		margin: 0;
		font-size: 0.76rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h2,
	p {
		margin: 0;
	}

	.lede {
		margin-top: 0.4rem;
		max-width: 58ch;
		color: #625a50;
		line-height: 1.6;
	}

	.header-actions {
		align-items: center;
	}

	.status-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 0.8rem;
	}

	.status-card {
		display: grid;
		gap: 0.35rem;
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 1.1rem;
		background: rgba(255, 255, 255, 0.82);
		padding: 0.9rem;
	}

	.status-card strong {
		color: #1d1b17;
		font-size: 1.05rem;
		text-transform: capitalize;
	}

	.notice,
	.loading-panel {
		border-radius: 1rem;
		padding: 0.95rem 1rem;
		background: rgba(255, 255, 255, 0.82);
	}

	.notice-warn {
		background: rgba(255, 248, 225, 0.92);
		color: #7f5d13;
	}

	.notice-error {
		background: rgba(255, 242, 238, 0.94);
		color: #7d3524;
	}

	.open-link,
	.secondary-button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.95rem;
		padding: 0.72rem 1.15rem;
		font: inherit;
		font-weight: 700;
		text-decoration: none;
	}

	.open-link {
		background: #1d9e75;
		color: #e1f5ee;
	}

	.secondary-button {
		border: none;
		background: rgba(36, 67, 106, 0.08);
		color: #24436a;
		cursor: pointer;
	}

	.skeleton-line {
		height: 0.8rem;
		border-radius: 999px;
		background: linear-gradient(
			90deg,
			rgba(229, 224, 214, 0.7),
			rgba(247, 243, 236, 0.95),
			rgba(229, 224, 214, 0.7)
		);
		background-size: 200% 100%;
		animation: shimmer 1.25s linear infinite;
	}

	.skeleton-line.short {
		width: 48%;
	}

	@keyframes shimmer {
		from {
			background-position: 200% 0;
		}
		to {
			background-position: -200% 0;
		}
	}

	@media (max-width: 720px) {
		.generation-header,
		.header-actions {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>
