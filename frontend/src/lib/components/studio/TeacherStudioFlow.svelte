<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';

	import { commitPlan, listContracts, streamPlan } from '$lib/api/brief';
	import { ApiError } from '$lib/api/errors';
	import GenerationView from '$lib/components/studio/GenerationView.svelte';
	import IntentForm from '$lib/components/studio/IntentForm.svelte';
	import PlanReview from '$lib/components/studio/PlanReview.svelte';
	import PlanStream from '$lib/components/studio/PlanStream.svelte';
	import {
		beginPlanning,
		briefDraft,
		completePlanning,
		contracts,
		editedSpec,
		failPlanning,
		generationState,
		planDraft,
		returnToIdle,
		setContracts,
		setGenerationAccepted,
		studioState
	} from '$lib/stores/studio';
	import { swapTemplateInSpec } from '$lib/studio/template-swap';
	import type {
		PlanningErrorEvent,
		PlanningTemplateSelectedEvent,
		StudioTemplateContract
	} from '$lib/types';

	let catalogError = $state<string | null>(null);
	let planningError = $state<string | null>(null);
	let commitError = $state<string | null>(null);
	let committing = $state(false);

	const stateSummary = $derived(
		$studioState === 'idle'
			? 'Intent capture'
			: $studioState === 'planning'
				? 'Live planning'
				: $studioState === 'reviewing'
					? 'Review'
					: 'Generating'
	);

	async function loadContractCatalog() {
		try {
			setContracts(await listContracts());
			catalogError = null;
		} catch (error) {
			catalogError =
				error instanceof ApiError || error instanceof Error
					? error.message
					: 'Failed to load template contracts.';
		}
	}

	async function handlePlan() {
		planningError = null;
		commitError = null;
		beginPlanning();

		const request = structuredClone(get(briefDraft));
		const startedAt = performance.now();

		try {
			for await (const event of streamPlan(request)) {
				if (event.event === 'template_selected') {
					const payload = (event as PlanningTemplateSelectedEvent).data;
					planDraft.update((draft) => ({
						...draft,
						template_decision: payload.template_decision,
						lesson_rationale: payload.lesson_rationale,
						warning: payload.warning
					}));
					continue;
				}

				if (event.event === 'section_planned') {
					planDraft.update((draft) => ({
						...draft,
						sections: [...draft.sections, event.data.section]
					}));
					continue;
				}

				if (event.event === 'plan_complete') {
					completePlanning(event.data.spec, performance.now() - startedAt);
					if (!get(contracts).length) {
						await loadContractCatalog();
					}
					continue;
				}

				const payload = (event as PlanningErrorEvent).data;
				completePlanning(payload.spec, performance.now() - startedAt);
				failPlanning(payload.warning ?? 'Planning fell back to defaults. Review carefully.');
				if (!get(contracts).length) {
					await loadContractCatalog();
				}
			}
		} catch (error) {
			planningError =
				error instanceof ApiError || error instanceof Error
					? error.message
					: 'Planning failed before a reviewable draft was returned.';
			returnToIdle();
		}
	}

	function handleTemplateSwap(contract: StudioTemplateContract) {
		const current = get(editedSpec);
		if (!current || current.template_id === contract.id) {
			return;
		}

		editedSpec.set(swapTemplateInSpec(current, contract));
	}

	async function handleCommit() {
		const spec = get(editedSpec);
		if (!spec) {
			return;
		}

		commitError = null;
		committing = true;

		try {
			const accepted = await commitPlan(spec);
			setGenerationAccepted(accepted);
			studioState.set('generating');
		} catch (error) {
			studioState.set('reviewing');
			commitError =
				error instanceof ApiError || error instanceof Error
					? error.message
					: 'Failed to start generation.';
		} finally {
			committing = false;
		}
	}

	function handleBackToBrief() {
		returnToIdle();
	}

	function handleResetFromGeneration() {
		returnToIdle();
	}

	onMount(() => {
		if (!get(contracts).length) {
			void loadContractCatalog();
		}
	});
</script>

<section class="studio-shell" data-state={$studioState}>
	<header class="studio-header">
		<div>
			<p class="eyebrow">Studio</p>
			<h1>Teacher lesson studio</h1>
			<p class="lede">
				Plan first, review explicitly, then watch generation unfold inside the workspace instead
				of being pushed straight into a separate page.
			</p>
		</div>

		<div class="studio-status">
			<span class="status-pill">{stateSummary}</span>
			<a href="/dashboard" class="dashboard-link">Back to dashboard</a>
		</div>
	</header>

	<div class="studio-grid">
		<div class="main-stage">
			{#if planningError}
				<p class="notice notice-error">{planningError}</p>
			{/if}

			{#if $studioState === 'idle'}
				<IntentForm onSubmit={handlePlan} />
			{:else if $studioState === 'planning'}
				<PlanStream />
			{:else if $studioState === 'reviewing'}
				<PlanReview
					busy={committing}
					onBack={handleBackToBrief}
					onCommit={handleCommit}
					onTemplateSwap={handleTemplateSwap}
					errorMessage={commitError}
				/>
			{:else if $generationState.accepted}
				<GenerationView accepted={$generationState.accepted} onReset={handleResetFromGeneration} />
			{/if}
		</div>

		<aside class="context-rail">
			<section class="rail-panel">
				<p class="rail-label">Workspace flow</p>
				<ol class="flow-list">
					<li class:flow-active={$studioState === 'idle'}>Capture teaching intent</li>
					<li class:flow-active={$studioState === 'planning'}>Stream the structure</li>
					<li class:flow-active={$studioState === 'reviewing'}>Review and swap templates</li>
					<li class:flow-active={$studioState === 'generating'}>Generate in place</li>
				</ol>
			</section>

			<section class="rail-panel">
				<p class="rail-label">Template catalog</p>
				<strong>{$contracts.length} live-safe templates</strong>
				<p class="rail-copy">
					The review state can switch between live-safe Lectio templates without another planner
					round-trip.
				</p>
				{#if catalogError}
					<p class="notice notice-error">{catalogError}</p>
				{/if}
			</section>

			<section class="rail-panel rail-panel-muted">
				<p class="rail-label">Current draft</p>
				<p class="rail-copy">
					Intent: {$briefDraft.intent || 'Waiting for a lesson brief.'}
				</p>
				<p class="rail-copy">
					Audience: {$briefDraft.audience || 'No audience set yet.'}
				</p>
			</section>
		</aside>
	</div>
</section>

<style>
	.studio-shell {
		display: grid;
		gap: 1.25rem;
	}

	.studio-header,
	.studio-status {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.eyebrow,
	.rail-label {
		margin: 0;
		font-size: 0.76rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h1,
	p {
		margin: 0;
	}

	h1 {
		font-size: clamp(2rem, 3vw, 2.8rem);
	}

	.lede {
		margin-top: 0.45rem;
		max-width: 62ch;
		color: #625a50;
		line-height: 1.65;
	}

	.studio-status {
		align-items: center;
	}

	.status-pill,
	.dashboard-link {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		padding: 0.45rem 0.8rem;
		font-size: 0.8rem;
		font-weight: 700;
		text-decoration: none;
	}

	.status-pill {
		background: rgba(29, 158, 117, 0.12);
		color: #0b6a52;
	}

	.dashboard-link {
		background: rgba(36, 67, 106, 0.08);
		color: #24436a;
	}

	.studio-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
		gap: 1rem;
		align-items: start;
	}

	.main-stage {
		display: grid;
		gap: 1rem;
	}

	.context-rail {
		display: grid;
		gap: 0.9rem;
		position: sticky;
		top: 1rem;
	}

	.rail-panel {
		display: grid;
		gap: 0.6rem;
		border-radius: 1.3rem;
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		background: rgba(255, 255, 255, 0.74);
		padding: 1rem;
		backdrop-filter: blur(12px);
	}

	.rail-panel-muted {
		background:
			linear-gradient(180deg, rgba(236, 246, 242, 0.78), rgba(255, 255, 255, 0.74)),
			rgba(255, 255, 255, 0.74);
	}

	.rail-copy {
		color: #625a50;
		line-height: 1.55;
	}

	.flow-list {
		display: grid;
		gap: 0.6rem;
		padding-left: 1.1rem;
		margin: 0;
		color: #625a50;
	}

	.flow-active {
		color: #0b6a52;
		font-weight: 700;
	}

	.notice {
		margin: 0;
		border-radius: 1rem;
		padding: 0.9rem 1rem;
	}

	.notice-error {
		background: rgba(255, 242, 238, 0.94);
		color: #7d3524;
	}

	@media (max-width: 980px) {
		.studio-grid {
			grid-template-columns: 1fr;
		}

		.context-rail {
			position: static;
		}
	}

	@media (max-width: 720px) {
		.studio-header,
		.studio-status {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>
