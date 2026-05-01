<script lang="ts">
	import SituationInput from '$lib/components/pack/SituationInput.svelte';
	import PackReview from '$lib/components/pack/PackReview.svelte';
	import PackGenerating from '$lib/components/pack/PackGenerating.svelte';
	import PackComplete from '$lib/components/pack/PackComplete.svelte';
	import { generateLearningPack } from '$lib/api/learning-pack';
	import type {
		LearningPackPlan,
		PackGenerateResponse,
		PackStatusResponse
	} from '$lib/types/learning-pack';

	type Step = 'input' | 'review' | 'generating' | 'complete';

	let step = $state<Step>('input');
	let packPlan = $state<LearningPackPlan | null>(null);
	let situation = $state('');
	let packResponse = $state<PackGenerateResponse | null>(null);
	let packStatus = $state<PackStatusResponse | null>(null);
	let starting = $state(false);
	let error = $state<string | null>(null);

	function onInterpreted(plan: LearningPackPlan, text: string) {
		packPlan = plan;
		situation = text;
		step = 'review';
	}

	async function onConfirmed(plan: LearningPackPlan) {
		starting = true;
		error = null;
		try {
			packResponse = await generateLearningPack(plan, situation);
			packPlan = plan;
			step = 'generating';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not start pack generation.';
		} finally {
			starting = false;
		}
	}

	function onComplete(status: PackStatusResponse) {
		packStatus = status;
		step = 'complete';
	}

	function restart() {
		step = 'input';
		packPlan = null;
		packResponse = null;
		packStatus = null;
		situation = '';
		error = null;
	}
</script>

<div class="pack-page">
	<nav class="steps">
		<span class:active={step === 'input'}>Situation</span>
		<span class:active={step === 'review'}>Review</span>
		<span class:active={step === 'generating'}>Generate</span>
		<span class:active={step === 'complete'}>Complete</span>
	</nav>

	<section class="surface">
		{#if step === 'input'}
			<SituationInput onInterpreted={onInterpreted} />
		{:else if step === 'review' && packPlan}
			<PackReview
				plan={packPlan}
				generating={starting}
				error={error}
				onBack={() => (step = 'input')}
				onConfirmed={onConfirmed}
			/>
		{:else if step === 'generating' && packResponse}
			<PackGenerating packId={packResponse.pack_id} onComplete={onComplete} />
		{:else if step === 'complete' && packStatus}
			<PackComplete packStatus={packStatus} onNewPack={restart} />
		{/if}
	</section>
</div>

<style>
	.pack-page {
		display: grid;
		gap: 1rem;
	}

	.steps {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.steps span {
		border-radius: 999px;
		background: rgba(36, 52, 63, 0.06);
		color: #5f574d;
		padding: 0.32rem 0.75rem;
		font-size: 0.82rem;
	}

	.steps .active {
		background: #24343f;
		color: #fff;
	}

	.surface {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 20px;
		background: rgba(255, 251, 244, 0.84);
		box-shadow: 0 18px 50px rgba(72, 52, 23, 0.08);
		padding: 1.35rem;
	}
</style>

