<script lang="ts">
	import {
		confidenceOptions,
		languageSupportOptions,
		learningPreferenceOptions,
		pacingOptions,
		priorKnowledgeOptions,
		readingLevelOptions
	} from '$lib/brief/config';
	import type {
		ClassConfidence,
		ClassLanguageSupport,
		ClassLearningPreference,
		ClassPacing,
		ClassPriorKnowledge,
		ClassProfile,
		ClassReadingLevel
	} from '$lib/types';

	interface Props {
		profile: ClassProfile;
		summary: string;
		onReadingLevelChange: (value: ClassReadingLevel) => void;
		onLanguageSupportChange: (value: ClassLanguageSupport) => void;
		onConfidenceChange: (value: ClassConfidence) => void;
		onPriorKnowledgeChange: (value: ClassPriorKnowledge) => void;
		onPacingChange: (value: ClassPacing) => void;
		onPreferenceToggle: (value: ClassLearningPreference) => void;
		onNotesInput: (value: string) => void;
		onSummaryInput: (value: string) => void;
		onContinue: () => void;
	}

	let {
		profile,
		summary,
		onReadingLevelChange,
		onLanguageSupportChange,
		onConfidenceChange,
		onPriorKnowledgeChange,
		onPacingChange,
		onPreferenceToggle,
		onNotesInput,
		onSummaryInput,
		onContinue
	}: Props = $props();
</script>

<div class="profile-step">
	<p class="helper">
		Capture the class profile in a structured way, then edit the learner summary so the planner
		can carry it forward into the frozen plan.
	</p>

	<div class="grid">
		<label class="field">
			<span>Reading level</span>
			<select
				value={profile.reading_level}
				onchange={(event) => onReadingLevelChange((event.currentTarget as HTMLSelectElement).value as ClassReadingLevel)}
			>
				{#each readingLevelOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
			<small>{readingLevelOptions.find((option) => option.value === profile.reading_level)?.description}</small>
		</label>

		<label class="field">
			<span>Language support</span>
			<select
				value={profile.language_support}
				onchange={(event) => onLanguageSupportChange((event.currentTarget as HTMLSelectElement).value as ClassLanguageSupport)}
			>
				{#each languageSupportOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
			<small>{languageSupportOptions.find((option) => option.value === profile.language_support)?.description}</small>
		</label>

		<label class="field">
			<span>Confidence</span>
			<select
				value={profile.confidence}
				onchange={(event) => onConfidenceChange((event.currentTarget as HTMLSelectElement).value as ClassConfidence)}
			>
				{#each confidenceOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
			<small>{confidenceOptions.find((option) => option.value === profile.confidence)?.description}</small>
		</label>

		<label class="field">
			<span>Prior knowledge</span>
			<select
				value={profile.prior_knowledge}
				onchange={(event) => onPriorKnowledgeChange((event.currentTarget as HTMLSelectElement).value as ClassPriorKnowledge)}
			>
				{#each priorKnowledgeOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
			<small>{priorKnowledgeOptions.find((option) => option.value === profile.prior_knowledge)?.description}</small>
		</label>

		<label class="field">
			<span>Pacing</span>
			<select
				value={profile.pacing}
				onchange={(event) => onPacingChange((event.currentTarget as HTMLSelectElement).value as ClassPacing)}
			>
				{#each pacingOptions as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
			<small>{pacingOptions.find((option) => option.value === profile.pacing)?.description}</small>
		</label>

		<label class="field field-notes">
			<span>Extra class notes</span>
			<textarea
				rows="3"
				value={profile.notes ?? ''}
				placeholder="Optional: IEP-heavy group, limited time, avoid long word problems..."
				oninput={(event) => onNotesInput((event.currentTarget as HTMLTextAreaElement).value)}
			></textarea>
		</label>
	</div>

	<div class="preferences">
		<p class="preference-label">Helpful learning preferences</p>
		<div class="chips">
			{#each learningPreferenceOptions as option}
				<button
					type="button"
					class:selected={profile.learning_preferences.includes(option.value)}
					class="chip"
					aria-pressed={profile.learning_preferences.includes(option.value)}
					onclick={() => onPreferenceToggle(option.value)}
				>
					{option.label}
				</button>
			{/each}
		</div>
	</div>

	<label class="field">
		<span>Learner summary</span>
		<textarea
			rows="5"
			value={summary}
			placeholder="Describe this class in teacher-friendly language."
			oninput={(event) => onSummaryInput((event.currentTarget as HTMLTextAreaElement).value)}
		></textarea>
	</label>

	<button type="button" class="primary" onclick={onContinue} disabled={!summary.trim()}>
		Continue
	</button>
</div>

<style>
	.profile-step {
		display: grid;
		gap: 0.95rem;
	}

	.helper,
	.preference-label,
	.field small {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 0.85rem;
	}

	.field {
		display: grid;
		gap: 0.4rem;
	}

	.field span,
	.preference-label {
		font-weight: 700;
	}

	.field-notes {
		grid-column: 1 / -1;
	}

	select,
	textarea {
		border: 1px solid rgba(36, 52, 63, 0.14);
		border-radius: 16px;
		padding: 0.85rem 0.95rem;
		font: inherit;
		background: #fffdf9;
	}

	textarea {
		resize: vertical;
	}

	.preferences {
		display: grid;
		gap: 0.6rem;
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
