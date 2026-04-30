<script lang="ts">
	import { gradeLevelLabel } from '$lib/brief/config';
	import type { TeacherGradeLevel, TopicResolutionSubtopic } from '$lib/types';

	interface Props {
		options: TopicResolutionSubtopic[];
		selected: string[];
		customValue: string;
		selectedGradeLevel?: TeacherGradeLevel;
		clarificationMessage?: string | null;
		onToggle: (value: string) => void;
		onCustomChange: (value: string) => void;
		onAddCustom: () => void;
		onContinue: () => void;
	}

	let {
		options,
		selected,
		customValue,
		selectedGradeLevel,
		clarificationMessage = null,
		onToggle,
		onCustomChange,
		onAddCustom,
		onContinue
	}: Props = $props();

	function badgeLabel(option: TopicResolutionSubtopic): string | null {
		if (!option.likely_grade_band) return null;
		if (!selectedGradeLevel || selectedGradeLevel === 'mixed') {
			return option.likely_grade_band;
		}
		const normalized = option.likely_grade_band.toLowerCase();
		if (
			normalized.includes('fit') ||
			normalized.includes('review') ||
			normalized.includes('challenge') ||
			normalized.includes('prerequisite')
		) {
			return option.likely_grade_band;
		}
		return `${gradeLevelLabel(selectedGradeLevel)} fit`;
	}
</script>

<div class="subtopics">
	<p class="helper">Choose 1 to 4 subtopics for this resource. The plan will consolidate them if the depth budget is tight.</p>

	{#if clarificationMessage}
		<p class="clarification">{clarificationMessage}</p>
	{/if}

	<div class="grid">
		{#each options as option}
			<button
				type="button"
				class:selected={selected.includes(option.title)}
				class="option-card"
				aria-pressed={selected.includes(option.title)}
				onclick={() => onToggle(option.title)}
			>
				<strong>{option.title}</strong>
				<span>{option.description}</span>
				{#if badgeLabel(option)}
					<small>{badgeLabel(option)}</small>
				{/if}
			</button>
		{/each}
	</div>

	<div class="custom">
		<label class="field">
			<span>Or add your own subtopic</span>
			<input
				type="text"
				value={customValue}
				placeholder="Solving two-step equations with negatives"
				oninput={(event) => onCustomChange((event.currentTarget as HTMLInputElement).value)}
			/>
		</label>
		<div class="actions">
			<button type="button" class="secondary" onclick={onAddCustom} disabled={!customValue.trim() || selected.length >= 4}>
				Add custom subtopic
			</button>
			<button type="button" class="primary" onclick={onContinue} disabled={selected.length === 0}>
				Continue
			</button>
		</div>
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

	.option-card.selected {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
		color: #085041;
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

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}

	.primary,
	.secondary {
		justify-self: start;
		border: 0;
		border-radius: 999px;
		padding: 0.75rem 1rem;
		font-weight: 700;
		cursor: pointer;
	}

	.primary {
		background: #1d9e75;
		color: white;
	}

	.secondary {
		background: #2f4858;
		color: white;
	}

	.secondary:disabled,
	.primary:disabled {
		opacity: 0.55;
		cursor: default;
	}
</style>
