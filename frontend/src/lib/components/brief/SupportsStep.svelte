<script lang="ts">
	import { supportOptions } from '$lib/brief/config';
	import type { TeacherBriefSupport } from '$lib/types';

	interface Props {
		selected: TeacherBriefSupport[];
		recommended: TeacherBriefSupport[];
		onToggle: (value: TeacherBriefSupport) => void;
		onContinue: () => void;
	}

	let { selected, recommended, onToggle, onContinue }: Props = $props();
</script>

<div class="supports-step">
	<p class="helper">Choose any supports you want to keep. Recommended supports are pre-selected.</p>
	<div class="chips">
		{#each supportOptions as option}
			<button
				type="button"
				class:selected={selected.includes(option.value)}
				class:recommended={recommended.includes(option.value)}
				class="chip"
				aria-pressed={selected.includes(option.value)}
				onclick={() => onToggle(option.value)}
			>
				{option.label}
				{#if recommended.includes(option.value)}
					<small>Recommended</small>
				{/if}
			</button>
		{/each}
	</div>

	<button type="button" class="primary" onclick={onContinue}>Continue</button>
</div>

<style>
	.supports-step {
		display: grid;
		gap: 0.9rem;
	}

	.helper {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.6rem;
	}

	.chip,
	.primary {
		border-radius: 999px;
		font-weight: 700;
		cursor: pointer;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		border: 1px solid rgba(36, 52, 63, 0.12);
		background: white;
		padding: 0.6rem 0.85rem;
	}

	.chip small {
		color: #7d5a21;
	}

	.chip.selected {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
		color: #085041;
	}

	.primary {
		justify-self: start;
		border: 0;
		background: #1d9e75;
		color: white;
		padding: 0.8rem 1.1rem;
	}
</style>
