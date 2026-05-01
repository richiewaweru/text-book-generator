<script lang="ts">
	import { interpretSituation, planLearningPack } from '$lib/api/learning-pack';
	import type { LearningPackPlan } from '$lib/types/learning-pack';

	let {
		onInterpreted
	}: { onInterpreted: (plan: LearningPackPlan, situation: string) => void } = $props();

	let situation = $state('');
	let loading = $state(false);
	let error = $state<string | null>(null);

	const examples = [
		'Year 7 struggled with slope last week, especially rise over run. Some ELL students.',
		'Grade 5 first lesson on plant germination. They need simple vocabulary and visuals.',
		'Quick check for grade 9 biology after teaching cell organelles yesterday.'
	];

	async function submit() {
		if (situation.trim().length < 5) return;
		loading = true;
		error = null;
		try {
			const job = await interpretSituation(situation);
			const plan = await planLearningPack(job);
			onInterpreted(plan, situation);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not plan this pack.';
		} finally {
			loading = false;
		}
	}
</script>

<section class="panel">
	<div>
		<p class="eyebrow">Learning pack</p>
		<h1>Describe the teaching situation</h1>
	</div>
	<textarea bind:value={situation} placeholder="What are you teaching, to whom, and what do they need?"></textarea>
	<div class="examples">
		{#each examples as example}
			<button type="button" onclick={() => (situation = example)}>{example}</button>
		{/each}
	</div>
	{#if error}
		<p class="error">{error}</p>
	{/if}
	<button class="primary" onclick={submit} disabled={loading || situation.trim().length < 5}>
		{loading ? 'Planning...' : 'Interpret and plan'}
	</button>
</section>

<style>
	.panel {
		display: grid;
		gap: 1rem;
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

	textarea {
		min-height: 12rem;
		resize: vertical;
		border: 1px solid rgba(36, 52, 63, 0.16);
		border-radius: 14px;
		padding: 1rem;
		font: inherit;
		background: rgba(255, 255, 255, 0.72);
	}

	.examples {
		display: grid;
		gap: 0.5rem;
	}

	.examples button,
	.primary {
		border: 1px solid rgba(36, 52, 63, 0.16);
		border-radius: 999px;
		padding: 0.55rem 0.85rem;
		background: rgba(255, 255, 255, 0.7);
		color: #24343f;
		cursor: pointer;
		text-align: left;
	}

	.primary {
		width: fit-content;
		background: #24343f;
		color: #fff;
		text-align: center;
	}

	.primary:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.error {
		color: #8d3a26;
	}
</style>
