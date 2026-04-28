<script lang="ts">
	import { gradeBandLabel, gradeLevelOptions } from '$lib/brief/config';
	import type { TeacherGradeBand, TeacherGradeLevel } from '$lib/types';

	interface Props {
		selected?: TeacherGradeLevel;
		derivedBand?: TeacherGradeBand | null;
		defaultGradeBandHint?: string | null;
		statusMessage?: string | null;
		loading?: boolean;
		onSelect: (value: TeacherGradeLevel) => void;
	}

	let {
		selected,
		derivedBand = null,
		defaultGradeBandHint = null,
		statusMessage = null,
		loading = false,
		onSelect
	}: Props = $props();
</script>

<div class="grade-step">
	<p class="helper">
		Choose the main grade level for this resource. The planner will use this to choose
		grade-appropriate subtopics.
	</p>

	{#if defaultGradeBandHint}
		<p class="hint">Your profile default is {defaultGradeBandHint}. Choose the exact grade for this resource.</p>
	{/if}

	<div class="grid">
		{#each gradeLevelOptions as option}
			<button
				type="button"
				class:selected={selected === option.value}
				class="option-card"
				aria-pressed={selected === option.value}
				disabled={loading}
				onclick={() => onSelect(option.value)}
			>
				<strong>{option.label}</strong>
				<span>{option.description}</span>
			</button>
		{/each}
	</div>

	{#if selected && derivedBand}
		<p class="band-summary" aria-live="polite">
			Derived band: <strong>{gradeBandLabel(derivedBand)}</strong>
		</p>
	{/if}

	{#if statusMessage}
		<p class="status" aria-live="polite">{statusMessage}</p>
	{/if}
</div>

<style>
	.grade-step {
		display: grid;
		gap: 0.9rem;
	}

	.helper,
	.hint,
	.band-summary,
	.status {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.hint {
		color: #4f5c65;
	}

	.band-summary strong {
		color: #1d1b17;
	}

	.status {
		color: #085041;
		font-weight: 600;
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

	.option-card.selected {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
		color: #085041;
	}

	.option-card:disabled {
		opacity: 0.65;
		cursor: default;
	}

	.option-card span {
		color: #655c52;
		line-height: 1.5;
	}
</style>
