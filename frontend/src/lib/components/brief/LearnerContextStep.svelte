<script lang="ts">
	interface Props {
		value: string;
		availableChips: string[];
		selectedChips: string[];
		onInput: (value: string) => void;
		onToggleChip: (chip: string) => void;
		onContinue: () => void;
	}

	let { value, availableChips, selectedChips, onInput, onToggleChip, onContinue }: Props = $props();
</script>

<div class="learner-step">
	<label class="field">
		<span>Who is this for?</span>
		<textarea
			rows="4"
			value={value}
			placeholder="Grade 7 students, mixed levels, some struggle with word problems."
			oninput={(event) => onInput((event.currentTarget as HTMLTextAreaElement).value)}
		></textarea>
	</label>

	<div class="chips">
		{#each availableChips as chip}
			<button
				type="button"
				class:selected={selectedChips.includes(chip)}
				class="chip"
				aria-pressed={selectedChips.includes(chip)}
				onclick={() => onToggleChip(chip)}
			>
				{chip}
			</button>
		{/each}
	</div>

	<button type="button" class="primary" onclick={onContinue} disabled={!value.trim() && selectedChips.length === 0}>
		Continue
	</button>
</div>

<style>
	.learner-step {
		display: grid;
		gap: 0.9rem;
	}

	.field {
		display: grid;
		gap: 0.45rem;
	}

	.field span {
		font-weight: 700;
	}

	textarea {
		border: 1px solid rgba(36, 52, 63, 0.14);
		border-radius: 16px;
		padding: 0.9rem 1rem;
		font: inherit;
		background: #fffdf9;
		resize: vertical;
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
		border: 1px solid rgba(36, 52, 63, 0.12);
		background: white;
		padding: 0.6rem 0.85rem;
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

	.primary:disabled {
		opacity: 0.6;
		cursor: default;
	}
</style>
