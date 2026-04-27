<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		stepLabel: string;
		active: boolean;
		completed: boolean;
		summary?: string;
		onEdit?: () => void;
		children: Snippet;
	}

	let {
		title,
		stepLabel,
		active,
		completed,
		summary = '',
		onEdit = () => {},
		children
	}: Props = $props();
</script>

<section class:active class:completed class="step-card">
	<header class="step-header">
		<div>
			<p class="step-label">{stepLabel}</p>
			<h2>{title}</h2>
		</div>
		{#if completed && !active}
			<button type="button" class="edit-button" onclick={onEdit}>Edit</button>
		{/if}
	</header>

	{#if active}
		<div class="step-body">
			{@render children()}
		</div>
	{:else if completed}
		<p class="step-summary">{summary}</p>
	{/if}
</section>

<style>
	.step-card {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 24px;
		background: rgba(255, 251, 244, 0.82);
		padding: 1.15rem;
		box-shadow: 0 16px 40px rgba(72, 52, 23, 0.08);
	}

	.step-card.completed:not(.active) {
		background: rgba(249, 244, 236, 0.72);
	}

	.step-card.active {
		border-color: rgba(29, 158, 117, 0.35);
		background: linear-gradient(180deg, rgba(244, 251, 248, 0.95), rgba(255, 251, 244, 0.95));
	}

	.step-header {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.step-label {
		margin: 0 0 0.25rem 0;
		font-size: 0.76rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h2,
	.step-summary {
		margin: 0;
	}

	h2 {
		font-size: 1.18rem;
	}

	.step-body {
		margin-top: 1rem;
	}

	.step-summary {
		margin-top: 0.85rem;
		color: #5d564e;
		line-height: 1.55;
	}

	.edit-button {
		border: 0;
		border-radius: 999px;
		background: #efe6d8;
		color: #2f4858;
		padding: 0.55rem 0.9rem;
		font-weight: 700;
		cursor: pointer;
	}
</style>
