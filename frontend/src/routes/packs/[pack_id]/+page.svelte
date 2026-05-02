<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import { downloadGenerationPdf } from '$lib/api/client';
	import { getPackStatus } from '$lib/api/learning-pack';
	import type { PDFExportRequest } from '$lib/types';
	import type { PackStatusResponse } from '$lib/types/learning-pack';
	import { getTextbookRoute } from '$lib/navigation/textbook';

	let status = $state<PackStatusResponse | null>(null);
	let error = $state<string | null>(null);
	let timer: ReturnType<typeof setInterval> | null = null;
	let exportOpen = $state(false);
	let schoolName = $state('');
	let teacherName = $state('');
	let exportDate = $state('');
	let exportPreset = $state<'teacher' | 'student'>('teacher');
	let includeToc = $state(true);
	let includeAnswers = $state(true);
	let selectedIds = $state<Set<string>>(new Set());
	let exportState = $state<'idle' | 'running' | 'done' | 'error'>('idle');
	let exportProgress = $state<{ current: number; total: number; label: string } | null>(null);
	let exportError = $state<string | null>(null);
	let lastExportTotal = $state(0);
	const packId = $derived(page.params.pack_id ?? '');
	const selectableResources = $derived(
		(status?.resources ?? []).filter(
			(resource) =>
				!!resource.generation_id &&
				(resource.status === 'completed' || resource.status === 'partial')
		)
	);
	const canBatchPrint = $derived(status?.status === 'complete' && selectableResources.length > 0);
	const selectedCount = $derived(
		selectableResources.filter(
			(resource) => !!resource.generation_id && selectedIds.has(resource.generation_id)
		).length
	);
	const exportDisabled = $derived(
		selectedCount === 0 ||
			schoolName.trim() === '' ||
			teacherName.trim() === '' ||
			exportState === 'running'
	);

	async function refresh() {
		try {
			status = await getPackStatus(packId);
			if (status.status === 'complete' || status.status === 'failed') {
				if (timer) clearInterval(timer);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load pack.';
		}
	}

	function initExportPanel() {
		selectedIds = new Set(
			selectableResources
				.map((resource) => resource.generation_id)
				.filter((generationId): generationId is string => !!generationId)
		);
		exportState = 'idle';
		exportProgress = null;
		exportError = null;
		lastExportTotal = 0;
	}

	function toggleExportPanel() {
		exportOpen = !exportOpen;
		if (exportOpen) {
			initExportPanel();
		}
	}

	function applyExportPreset(preset: 'teacher' | 'student') {
		exportPreset = preset;
		includeToc = true;
		includeAnswers = preset === 'teacher';
	}

	function toggleSelected(generationId: string | null) {
		if (!generationId) {
			return;
		}
		const next = new Set(selectedIds);
		if (next.has(generationId)) {
			next.delete(generationId);
		} else {
			next.add(generationId);
		}
		selectedIds = next;
	}

	async function handleBatchExport() {
		const targets = selectableResources.filter(
			(resource) => !!resource.generation_id && selectedIds.has(resource.generation_id)
		);
		if (targets.length === 0) {
			return;
		}

		exportState = 'running';
		exportError = null;
		lastExportTotal = targets.length;

		const request: PDFExportRequest = {
			school_name: schoolName.trim(),
			teacher_name: teacherName.trim(),
			include_toc: includeToc,
			include_answers: includeAnswers
		};
		if (exportDate.trim()) {
			request.date = exportDate.trim();
		}

		for (let index = 0; index < targets.length; index += 1) {
			const resource = targets[index];
			if (!resource.generation_id) {
				continue;
			}
			exportProgress = {
				current: index + 1,
				total: targets.length,
				label: resource.label
			};
			try {
				await downloadGenerationPdf(resource.generation_id, request);
			} catch (err) {
				exportError = `Failed on "${resource.label}": ${
					err instanceof Error ? err.message : 'Unknown error'
				}`;
				exportState = 'error';
				exportProgress = null;
				return;
			}
		}

		exportProgress = null;
		exportState = 'done';
	}

	onMount(() => {
		void refresh();
		timer = setInterval(() => void refresh(), 3000);
	});

	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

<section class="pack-view">
	{#if error}
		<p class="error">{error}</p>
	{:else if status}
		<div class="header">
			<div>
				<p class="eyebrow">{status.learning_job_type}</p>
				<h1>{status.topic}</h1>
				<p>{status.completed_count} of {status.resource_count} ready - {status.status}</p>
			</div>
			{#if canBatchPrint}
				<button type="button" class="print-btn" onclick={toggleExportPanel}>
					{exportOpen ? 'Close' : 'Print Pack'}
				</button>
			{/if}
		</div>

		{#if exportOpen && canBatchPrint}
			<div class="export-panel">
				<h2>Print Pack</h2>
				<div class="export-fields">
					<label>
						<span>School name</span>
						<input bind:value={schoolName} placeholder="Springfield High" />
					</label>
					<label>
						<span>Teacher name</span>
						<input bind:value={teacherName} placeholder="Ms. Johnson" />
					</label>
					<label>
						<span>Date</span>
						<input bind:value={exportDate} type="date" />
					</label>
				</div>

				<div class="preset-row">
					<button
						type="button"
						class:active={exportPreset === 'teacher'}
						onclick={() => applyExportPreset('teacher')}
					>
						Teacher copy
					</button>
					<button
						type="button"
						class:active={exportPreset === 'student'}
						onclick={() => applyExportPreset('student')}
					>
						Student copy
					</button>
				</div>

				<div class="resource-list">
					{#each status.resources as resource}
						{@const selectable = !!resource.generation_id &&
							(resource.status === 'completed' || resource.status === 'partial')}
						<label class:disabled={!selectable}>
							<input
								type="checkbox"
								disabled={!selectable || exportState === 'running'}
								checked={selectable &&
									!!resource.generation_id &&
									selectedIds.has(resource.generation_id)}
								onchange={() => toggleSelected(resource.generation_id)}
							/>
							<span>{resource.label}</span>
							<span class="resource-type">
								{resource.resource_type.replaceAll('_', ' ')}
								{#if !selectable && resource.status === 'failed'}
									- failed
								{/if}
							</span>
						</label>
					{/each}
				</div>

				<button
					type="button"
					class="export-btn"
					disabled={exportDisabled}
					onclick={handleBatchExport}
				>
					{exportState === 'running' && exportProgress
						? `Exporting ${exportProgress.current} of ${exportProgress.total}...`
						: `Export ${selectedCount} PDF${selectedCount === 1 ? '' : 's'}`}
				</button>

				{#if exportState === 'running' && exportProgress}
					<p class="progress-label">
						Exporting {exportProgress.current} of {exportProgress.total}: {exportProgress.label}...
					</p>
				{/if}
				{#if exportState === 'done'}
					<p class="done-label">
						Done. {lastExportTotal} PDF{lastExportTotal === 1 ? '' : 's'} exported.
					</p>
				{/if}
				{#if exportState === 'error' && exportError}
					<p class="error-label">{exportError}</p>
				{/if}
			</div>
		{/if}

		<div class="resources">
			{#each status.resources as resource}
				<article>
					<strong>{resource.label}</strong>
					<p>{resource.resource_type.replaceAll('_', ' ')} - {resource.phase}</p>
					{#if resource.generation_id}
						<a href={getTextbookRoute(resource.generation_id)}>Open</a>
					{/if}
				</article>
			{/each}
		</div>
	{:else}
		<p>Loading pack...</p>
	{/if}
</section>

<style>
	.pack-view {
		display: grid;
		gap: 1rem;
	}

	.header,
	.resources article {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: rgba(255, 251, 244, 0.84);
		padding: 1rem;
	}

	.header {
		display: flex;
		gap: 0.75rem;
		justify-content: space-between;
		align-items: flex-start;
	}

	.print-btn {
		padding: 0.45rem 1rem;
		border-radius: 999px;
		background: #24343f;
		color: #fff;
		font-size: 0.82rem;
		font-weight: 600;
		border: none;
		cursor: pointer;
	}

	.export-panel {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: rgba(255, 251, 244, 0.84);
		padding: 1.25rem;
		display: grid;
		gap: 1rem;
	}

	.export-panel h2 {
		margin: 0;
		font-size: 1rem;
		font-weight: 700;
	}

	.export-fields {
		display: grid;
		gap: 0.6rem;
	}

	.export-fields label {
		display: grid;
		gap: 0.25rem;
	}

	.export-fields span {
		font-size: 0.78rem;
		color: #6b7c88;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.export-fields input {
		padding: 0.4rem 0.6rem;
		border: 1px solid rgba(36, 52, 63, 0.18);
		border-radius: 8px;
		background: #fff;
		font-size: 0.88rem;
	}

	.preset-row {
		display: flex;
		gap: 0.5rem;
	}

	.preset-row button {
		padding: 0.35rem 0.85rem;
		border-radius: 999px;
		border: 1px solid rgba(36, 52, 63, 0.18);
		background: transparent;
		font-size: 0.82rem;
		cursor: pointer;
	}

	.preset-row button.active {
		background: #24343f;
		color: #fff;
		border-color: #24343f;
	}

	.resource-list {
		display: grid;
		gap: 0.45rem;
	}

	.resource-list label {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		font-size: 0.88rem;
		cursor: pointer;
	}

	.resource-list label.disabled {
		opacity: 0.45;
		cursor: default;
	}

	.resource-type {
		font-size: 0.78rem;
		color: #6b7c88;
	}

	.export-btn {
		padding: 0.55rem 1.25rem;
		border-radius: 999px;
		background: #24343f;
		color: #fff;
		font-size: 0.88rem;
		font-weight: 600;
		border: none;
		cursor: pointer;
		justify-self: start;
	}

	.export-btn:disabled {
		opacity: 0.45;
		cursor: default;
	}

	.progress-label {
		font-size: 0.82rem;
		color: #6b7c88;
		margin: 0;
	}

	.done-label {
		font-size: 0.82rem;
		color: #2a6049;
		margin: 0;
	}

	.error-label {
		font-size: 0.82rem;
		color: #8d3a26;
		margin: 0;
	}

	.eyebrow,
	h1,
	p {
		margin: 0;
	}

	.eyebrow {
		font-size: 0.78rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	.resources {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 0.75rem;
	}

	.resources article {
		display: grid;
		gap: 0.45rem;
	}

	a {
		color: #24436a;
		font-weight: 700;
		text-decoration: none;
	}

	.error {
		color: #8d3a26;
	}
</style>
