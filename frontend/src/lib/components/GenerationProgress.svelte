<script lang="ts">
	import type { GenerationStatus } from '$lib/types';
	import { hasRetryContext, progressPercent, resolveGenerationMode } from '$lib/generation/progress';

	interface Props {
		status: GenerationStatus;
	}

	let { status }: Props = $props();
	let mode = $derived(resolveGenerationMode(status));
	let percent = $derived(progressPercent(status.progress));
</script>

<div class="progress">
	<div class="header">
		<p>Status: <strong>{status.status}</strong></p>
		{#if mode}
			<span class="mode-badge mode-{mode}">{mode}</span>
		{/if}
	</div>

	{#if status.progress}
		<p class="phase">{status.progress.phase}</p>
		<p class="message">{status.progress.message}</p>
		{#if status.progress.sections_total}
			<p>
				{status.progress.sections_completed} / {status.progress.sections_total} sections ready
			</p>
			<div class="bar">
				<div class="fill" style={`width:${percent}%`}></div>
			</div>
		{/if}
		{#if status.progress.current_section_title}
			<p class="section">Current section: {status.progress.current_section_title}</p>
		{/if}
		{#if hasRetryContext(status.progress)}
			<p class="retry">
				Retry {status.progress.retry_attempt} of {status.progress.retry_limit}
			</p>
		{/if}
		{#if status.progress.flagged_section_ids.length > 0}
			<p class="retry">Flagged sections: {status.progress.flagged_section_ids.join(', ')}</p>
		{/if}
	{/if}

	{#if status.error}
		<p class="error">{status.error}</p>
	{/if}
</div>

<style>
	.progress {
		background: #151515;
		border: 1px solid #303030;
		border-radius: 10px;
		padding: 1rem;
		display: grid;
		gap: 0.4rem;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
	}

	.header p,
	.message,
	.phase,
	.section,
	.retry,
	.error {
		margin: 0;
	}

	.phase {
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-size: 0.75rem;
		color: #8aa1c1;
	}

	.message {
		color: #e5e5e5;
	}

	.section,
	.retry {
		color: #9a9a9a;
		font-size: 0.9rem;
	}

	.bar {
		height: 0.5rem;
		background: #242424;
		border-radius: 999px;
		overflow: hidden;
	}

	.fill {
		height: 100%;
		background: linear-gradient(90deg, #4a86d6, #6aa7f0);
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

	.error {
		color: #e57373;
	}
</style>
