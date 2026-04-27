<script lang="ts">
	import type { TopicResolutionSubtopic } from '$lib/types';

	interface Props {
		options: TopicResolutionSubtopic[];
		customValue: string;
		clarificationMessage?: string | null;
		onSelect: (value: string) => void;
		onCustomChange: (value: string) => void;
		onUseCustom: () => void;
	}

	let {
		options,
		customValue,
		clarificationMessage = null,
		onSelect,
		onCustomChange,
		onUseCustom
	}: Props = $props();
</script>

<div class="subtopics">
	<p class="helper">Choose the exact focus for this resource.</p>

	{#if clarificationMessage}
		<p class="clarification">{clarificationMessage}</p>
	{/if}

	<div class="grid">
		{#each options as option}
			<button type="button" class="option-card" onclick={() => onSelect(option.title)}>
				<strong>{option.title}</strong>
				<span>{option.description}</span>
				{#if option.likely_grade_band}
					<small>{option.likely_grade_band}</small>
				{/if}
			</button>
		{/each}
	</div>

	<div class="custom">
		<label class="field">
			<span>Or type your own subtopic</span>
			<input
				type="text"
				value={customValue}
				placeholder="Solving two-step equations with negatives"
				oninput={(event) => onCustomChange((event.currentTarget as HTMLInputElement).value)}
			/>
		</label>
		<button type="button" class="secondary" onclick={onUseCustom} disabled={!customValue.trim()}>
			Use custom subtopic
		</button>
	</div>
</div>

<style>
	.subtopics,
	.custom {
		display: grid;
		gap: 0.9rem;
	}

	.helper,
	.clarification {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.clarification {
		color: #7d5a21;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 0.8rem;
	}

	.option-card {
		display: grid;
		gap: 0.4rem;
		text-align: left;
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: white;
		padding: 1rem;
		cursor: pointer;
	}

	.option-card span,
	.option-card small {
		color: #655c52;
		line-height: 1.5;
	}

	.field {
		display: grid;
		gap: 0.45rem;
	}

	input {
		border: 1px solid rgba(36, 52, 63, 0.14);
		border-radius: 16px;
		padding: 0.9rem 1rem;
		font: inherit;
		background: #fffdf9;
	}

	.secondary {
		justify-self: start;
		border: 0;
		border-radius: 999px;
		background: #2f4858;
		color: white;
		padding: 0.75rem 1rem;
		font-weight: 700;
		cursor: pointer;
	}

	.secondary:disabled {
		opacity: 0.55;
		cursor: default;
	}
</style>
