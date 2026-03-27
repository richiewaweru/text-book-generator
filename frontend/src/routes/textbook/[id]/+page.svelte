<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import LectioDocumentView from '$lib/components/LectioDocumentView.svelte';
	import {
		applySectionFailed,
		applySectionReady,
		applySectionStarted,
		buildSectionSlots,
		normalizeDocument
	} from '$lib/generation/viewer-state';
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
		ProgressUpdateEvent,
		SectionFailedEvent,
		SectionReadyEvent,
		SectionStartedEvent
	} from '$lib/types';

	const generationId = $derived(page.params.id);

	let detail = $state<GenerationDetail | null>(null);
	let document = $state<GenerationDocument | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let enhancing = $state(false);
	let streamState = $state<'idle' | 'connected' | 'reconnecting' | 'complete'>('idle');
	let plannedSections = $state<number | null>(null);
	let qcSummary = $state<{ passed: number; total: number } | null>(null);
	let progressUpdate = $state<ProgressUpdateEvent | null>(null);
	let viewerWarning = $state<string | null>(null);
	let eventSource: EventSource | null = null;
	let streamClosedTerminally = false;
	let streamErrorRecoveryAttempted = false;
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
	const progressStageLabel = $derived(
		progressUpdate?.stage ? progressUpdate.stage.replaceAll('_', ' ') : null
	);
	const sectionTitleMap = $derived(buildSectionTitleMap(document));
	const weakSections = $derived(buildWeakSectionSummaries(document, sectionTitleMap));

	function closeStream(source: EventSource | null = eventSource) {
		source?.close();
		if (source === eventSource) {
			eventSource = null;
		}
	}

	function buildSectionTitleMap(nextDocument: GenerationDocument | null): Map<string, string> {
		const map = new Map<string, string>();
		if (!nextDocument) {
			return map;
		}

		for (const item of nextDocument.section_manifest) {
			map.set(item.section_id, item.title);
		}
		for (const section of nextDocument.sections) {
			map.set(section.section_id, section.header.title);
		}
		for (const failed of nextDocument.failed_sections) {
			map.set(failed.section_id, failed.title);
		}

		return map;
	}

	function buildWeakSectionSummaries(
		nextDocument: GenerationDocument | null,
		titleMap: Map<string, string>
	): Array<{
		section_id: string;
		title: string;
		warning: string;
		issues: GenerationDocument['qc_reports'][number]['issues'];
	}> {
		if (!nextDocument) {
			return [];
		}

		const failedIds = new Set(nextDocument.failed_sections.map((entry) => entry.section_id));

		return nextDocument.qc_reports
			.filter((report) => !failedIds.has(report.section_id))
			.filter((report) => !report.passed || report.warnings.length > 0)
			.map((report) => ({
				section_id: report.section_id,
				title: titleMap.get(report.section_id) ?? report.section_id,
				warning:
					report.warnings[0] ??
					report.issues[0]?.message ??
					'This section may benefit from another pass.',
				issues: report.issues
			}));
	}

	function hasDiagramIssue(issues: GenerationDocument['qc_reports'][number]['issues']): boolean {
		return issues.some((issue) => issue.block.includes('diagram'));
	}

	async function requestEnhancement(options: {
		scope: 'section' | 'component';
		sectionId: string;
		component?: string;
		label: string;
	}) {
		if (!generationId) {
			return;
		}

		enhancing = true;
		error = null;

		try {
			const accepted = await enhanceGeneration(generationId, {
				mode: 'balanced',
				scope: options.scope,
				section_id: options.sectionId,
				component: options.component,
				note: options.label
			});
			goto(`/textbook/${accepted.generation_id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to enhance draft.';
		} finally {
			enhancing = false;
		}
	}

	function applyGenerationSnapshot(nextDetail: GenerationDetail, nextDocument: GenerationDocument) {
		const normalizedDocument = normalizeDocument(nextDocument);
		const manifestCount = normalizedDocument.section_manifest.length;
		const sectionCount = normalizedDocument.sections.length;
		detail = nextDetail;
		document = normalizedDocument;
		plannedSections =
			nextDetail.section_count ?? (manifestCount > 0 ? manifestCount : sectionCount > 0 ? sectionCount : null);
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
		} catch (err) {
			console.error('[Lectio] Stream recovery refresh failed:', err);
			return false;
		}
		if (source !== eventSource) {
			return false;
		}
		if (detail?.status === 'completed' || detail?.status === 'failed') {
			streamClosedTerminally = true;
			streamState = 'complete';
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

		source.addEventListener('pipeline_start', (event) => {
			if (source !== eventSource) {
				return;
			}
			const payload = JSON.parse((event as MessageEvent).data) as { section_count: number };
			plannedSections = payload.section_count;
		});

		source.addEventListener('progress_update', (event) => {
			if (source !== eventSource) {
				return;
			}
			progressUpdate = JSON.parse((event as MessageEvent).data) as ProgressUpdateEvent;
		});

		source.addEventListener('section_started', (event) => {
			if (source !== eventSource) {
				return;
			}
			const payload = JSON.parse((event as MessageEvent).data) as SectionStartedEvent;
			if (!document) {
				return;
			}
			document = applySectionStarted(document, payload);
		});

		source.addEventListener('section_ready', (event) => {
			if (source !== eventSource) {
				return;
			}
			const payload = JSON.parse((event as MessageEvent).data) as SectionReadyEvent;
			plannedSections = payload.total_sections;
			if (!document) {
				return;
			}
			const result = applySectionReady(document, payload);
			document = result.document;
			if (result.warning) {
				console.error('[Lectio] Section validation failed:', result.warning.message);
				viewerWarning = result.warning.message;
			}
		});

		source.addEventListener('section_failed', (event) => {
			if (source !== eventSource) {
				return;
			}
			const payload = JSON.parse((event as MessageEvent).data) as SectionFailedEvent;
			if (!document) {
				return;
			}
			document = applySectionFailed(document, payload);
		});

		source.addEventListener('qc_complete', (event) => {
			if (source !== eventSource) {
				return;
			}
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
				closeStream(source);
				return;
			}
			if (await revalidateTerminalState(source, id)) {
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
		progressUpdate = null;
		viewerWarning = null;
		streamClosedTerminally = false;
		streamErrorRecoveryAttempted = false;
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

	async function handleSectionEnhance(sectionId: string) {
		await requestEnhancement({
			scope: 'section',
			sectionId,
			label: 'Improve this section'
		});
	}

	async function handleDiagramEnhance(sectionId: string) {
		await requestEnhancement({
			scope: 'component',
			sectionId,
			component: 'diagram',
			label: 'Retry the diagram'
		});
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
				Sections ready: {readySectionCount} / {plannedSections}
			</p>
			{#if failedSectionCount > 0}
				<p>Failed sections: {failedSectionCount}</p>
			{/if}
			<p>Stream: {streamLabel}</p>
			{#if progressUpdate && detail?.status !== 'completed' && detail?.status !== 'failed'}
				<p>Progress: {progressUpdate.label}</p>
				<p>Stage: {progressStageLabel}</p>
			{/if}
			{#if qcSummary}
				<p>QC: {qcSummary.passed} / {qcSummary.total} passing</p>
			{/if}
		</div>
	{/if}

	{#if viewerWarning}
		<div class="warning"><strong>Viewer warning:</strong> {viewerWarning}</div>
	{/if}

	{#if detail?.mode === 'draft'}
		<p class="draft-note">
			Draft mode is the fast seedable pass. Use Enhance Draft to keep the section structure and let
			the pipeline rework it in balanced mode.
		</p>
	{/if}

	{#if document?.failed_sections?.length}
		<section class="failed-sections">
			<h2>Sections Not Completed</h2>
			<ul>
				{#each document.failed_sections as failed}
					<li>
						<div class="section-summary">
							<strong>{failed.title}</strong>
							<span>Failed at {failed.failed_at_node}: {failed.error_summary}</span>
						</div>
						<div class="section-actions">
							<button
								type="button"
								class="section-action"
								onclick={() => handleSectionEnhance(failed.section_id)}
								disabled={enhancing}
							>
								Improve section
							</button>
							{#if failed.needs_diagram || failed.missing_components.some((component) => component.includes('diagram'))}
								<button
									type="button"
									class="section-action"
									onclick={() => handleDiagramEnhance(failed.section_id)}
									disabled={enhancing}
								>
									Retry diagram
								</button>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if weakSections.length}
		<section class="weak-sections">
			<h2>Sections Needing Another Pass</h2>
			<ul>
				{#each weakSections as weak}
					<li>
						<div class="section-summary">
							<strong>{weak.title}</strong>
							<span>{weak.warning}</span>
						</div>
						<div class="section-actions">
							<button
								type="button"
								class="section-action"
								onclick={() => handleSectionEnhance(weak.section_id)}
								disabled={enhancing}
							>
								Improve section
							</button>
							{#if hasDiagramIssue(weak.issues)}
								<button
									type="button"
									class="section-action"
									onclick={() => handleDiagramEnhance(weak.section_id)}
									disabled={enhancing}
								>
									Retry diagram
								</button>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if error}
		<div class="error"><strong>Error:</strong> {error}</div>
	{:else if loading}
		<p>Loading generation...</p>
	{:else if document}
		<LectioDocumentView {document} sectionSlots={sectionSlots} />
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
	.failed-sections,
	.weak-sections,
	.warning,
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

	.warning {
		border-color: rgba(169, 129, 37, 0.18);
		background: rgba(255, 248, 225, 0.92);
		color: #7f5d13;
	}

	.failed-sections ul {
		margin: 0.75rem 0 0 0;
		padding-left: 1.1rem;
		display: grid;
		gap: 0.55rem;
	}

	.failed-sections li {
		display: grid;
		gap: 0.2rem;
	}

	.section-summary {
		display: grid;
		gap: 0.15rem;
	}

	.section-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem;
		margin-top: 0.45rem;
	}

	.section-action {
		border-radius: 999px;
		border: 1px solid rgba(36, 67, 106, 0.16);
		background: rgba(36, 67, 106, 0.06);
		color: #24436a;
		padding: 0.45rem 0.8rem;
		font: inherit;
		cursor: pointer;
	}

	.section-action:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
