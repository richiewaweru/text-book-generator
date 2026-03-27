<script lang="ts">
	import { get } from 'svelte/store';

	import { briefDraft } from '$lib/stores/studio';
	import type {
		Brevity,
		ClassStyle,
		ExplanationStyle,
		LearningOutcome,
		LessonFormat,
		ReadingLevel,
		Tone,
		TopicType,
		UserBriefDraft
	} from '$lib/types';

	interface Props {
		disabled?: boolean;
		onSubmit: () => void;
	}

	type SignalKey = keyof UserBriefDraft['signals'];
	type PreferenceKey = keyof UserBriefDraft['preferences'];
	type ConstraintKey = keyof UserBriefDraft['constraints'];

	let { disabled = false, onSubmit }: Props = $props();
	let showPriorKnowledge = $state(false);
	let showPreferences = $state(false);
	let validationMessage = $state<string | null>(null);

	const topicTypes: Array<{ label: string; value: TopicType }> = [
		{ label: 'Concept / idea', value: 'concept' },
		{ label: 'Step-by-step process', value: 'process' },
		{ label: 'Facts to remember', value: 'facts' },
		{ label: 'Mixed', value: 'mixed' }
	];

	const learningOutcomes: Array<{ label: string; value: LearningOutcome }> = [
		{ label: 'Understand why it works', value: 'understand-why' },
		{ label: 'Be able to do it themselves', value: 'be-able-to-do' },
		{ label: 'Remember key terms', value: 'remember-terms' },
		{ label: 'Apply to a new situation', value: 'apply-to-new' }
	];

	const classStyles: Array<{ label: string; value: ClassStyle }> = [
		{ label: 'Needs explanation first', value: 'needs-explanation-first' },
		{ label: 'Tries before being told', value: 'tries-before-told' },
		{ label: 'Gets restless without activity', value: 'restless-without-activity' },
		{ label: 'Responds to visuals', value: 'engages-with-visuals' },
		{ label: 'Likes worked examples', value: 'responds-to-worked-examples' }
	];

	const formats: Array<{ label: string; value: LessonFormat }> = [
		{ label: 'Printed booklet', value: 'printed-booklet' },
		{ label: 'Screen-based', value: 'screen-based' },
		{ label: 'Both', value: 'both' }
	];

	const tones: Array<{ label: string; value: Tone }> = [
		{ label: 'Supportive', value: 'supportive' },
		{ label: 'Neutral', value: 'neutral' },
		{ label: 'Rigorous', value: 'rigorous' }
	];

	const readingLevels: Array<{ label: string; value: ReadingLevel }> = [
		{ label: 'Simple', value: 'simple' },
		{ label: 'Standard', value: 'standard' },
		{ label: 'Advanced', value: 'advanced' }
	];

	const explanationStyles: Array<{ label: string; value: ExplanationStyle }> = [
		{ label: 'Concrete examples first', value: 'concrete-first' },
		{ label: 'Concept first', value: 'concept-first' },
		{ label: 'Balanced', value: 'balanced' }
	];

	const brevityOptions: Array<{ label: string; value: Brevity }> = [
		{ label: 'Concise', value: 'tight' },
		{ label: 'Balanced', value: 'balanced' },
		{ label: 'Expanded', value: 'expanded' }
	];

	function updateBrief(patch: Partial<UserBriefDraft>) {
		briefDraft.update((draft) => ({
			...draft,
			...patch
		}));
	}

	function updateSignals<K extends SignalKey>(key: K, value: UserBriefDraft['signals'][K]) {
		briefDraft.update((draft) => ({
			...draft,
			signals: {
				...draft.signals,
				[key]: value
			}
		}));
	}

	function updatePreferences<K extends PreferenceKey>(
		key: K,
		value: UserBriefDraft['preferences'][K]
	) {
		briefDraft.update((draft) => ({
			...draft,
			preferences: {
				...draft.preferences,
				[key]: value
			}
		}));
	}

	function updateConstraints<K extends ConstraintKey>(
		key: K,
		value: UserBriefDraft['constraints'][K]
	) {
		briefDraft.update((draft) => ({
			...draft,
			constraints: {
				...draft.constraints,
				[key]: value
			}
		}));
	}

	function toggleClassStyle(value: ClassStyle) {
		const current = get(briefDraft).signals.class_style;
		if (current.includes(value)) {
			updateSignals(
				'class_style',
				current.filter((item) => item !== value)
			);
			return;
		}
		if (current.length >= 3) {
			return;
		}
		updateSignals('class_style', [...current, value]);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();

		const draft = get(briefDraft);
		if (!draft.intent.trim() || !draft.audience.trim()) {
			validationMessage = 'Intent and audience are both required.';
			return;
		}

		validationMessage = null;
		onSubmit();
	}
</script>

<form class="studio-form" onsubmit={handleSubmit}>
	<div class="form-card">
		<div class="heading">
			<div>
				<p class="eyebrow">Teacher Studio</p>
				<h1>Shape the lesson before generation</h1>
				<p class="lede">
					Capture the teaching intent, signal the learning shape, then let the planner assemble
					a reviewable lesson structure.
				</p>
			</div>
		</div>

		{#if validationMessage}
			<p class="notice notice-error">{validationMessage}</p>
		{/if}

		<div class="field-grid">
			<label class="field field-wide">
				<span>What do you want to teach?</span>
				<input
					type="text"
					value={$briefDraft.intent}
					placeholder="Explain photosynthesis to Year 10 students"
					oninput={(event) =>
						updateBrief({ intent: (event.currentTarget as HTMLInputElement).value })}
					disabled={disabled}
				/>
			</label>

			<label class="field field-wide">
				<span>Who is this for?</span>
				<input
					type="text"
					value={$briefDraft.audience}
					placeholder="Year 10, mixed ability, 45-minute class"
					oninput={(event) =>
						updateBrief({ audience: (event.currentTarget as HTMLInputElement).value })}
					disabled={disabled}
				/>
			</label>
		</div>

		<button class="toggle-link" type="button" onclick={() => (showPriorKnowledge = !showPriorKnowledge)}>
			{showPriorKnowledge ? '-' : '+'} Prior knowledge and extra context
		</button>

		{#if showPriorKnowledge}
			<div class="field-grid">
				<label class="field">
					<span>Prior knowledge</span>
					<textarea
						rows="3"
						value={$briefDraft.prior_knowledge}
						placeholder="What do students already know? (optional)"
						oninput={(event) =>
							updateBrief({
								prior_knowledge: (event.currentTarget as HTMLTextAreaElement).value
							})}
						disabled={disabled}
					></textarea>
				</label>

				<label class="field">
					<span>Extra context</span>
					<textarea
						rows="3"
						value={$briefDraft.extra_context}
						placeholder="Any extra context or lesson constraints? (optional)"
						oninput={(event) =>
							updateBrief({
								extra_context: (event.currentTarget as HTMLTextAreaElement).value
							})}
						disabled={disabled}
					></textarea>
				</label>
			</div>
		{/if}

		<div class="signal-stack">
			<div class="signal-block">
				<p class="signal-title">Topic type</p>
				<div class="chip-row">
					{#each topicTypes as option}
						<button
							type="button"
							class:chip-selected={$briefDraft.signals.topic_type === option.value}
							class="chip"
							onclick={() => updateSignals('topic_type', option.value)}
						>
							{option.label}
						</button>
					{/each}
				</div>
			</div>

			<div class="signal-block">
				<p class="signal-title">Learning outcome</p>
				<div class="chip-row">
					{#each learningOutcomes as option}
						<button
							type="button"
							class:chip-selected={$briefDraft.signals.learning_outcome === option.value}
							class="chip"
							onclick={() => updateSignals('learning_outcome', option.value)}
						>
							{option.label}
						</button>
					{/each}
				</div>
			</div>

			<div class="signal-block">
				<p class="signal-title">How the class learns</p>
				<div class="chip-row">
					{#each classStyles as option}
						<button
							type="button"
							class:chip-selected={$briefDraft.signals.class_style.includes(option.value)}
							class="chip"
							onclick={() => toggleClassStyle(option.value)}
						>
							{option.label}
						</button>
					{/each}
				</div>
				<p class="helper">Select up to 3.</p>
			</div>

			<div class="signal-block">
				<p class="signal-title">Format</p>
				<div class="chip-row">
					{#each formats as option}
						<button
							type="button"
							class:chip-selected={$briefDraft.signals.format === option.value}
							class="chip"
							onclick={() => updateSignals('format', option.value)}
						>
							{option.label}
						</button>
					{/each}
				</div>
			</div>
		</div>

		<button class="toggle-link" type="button" onclick={() => (showPreferences = !showPreferences)}>
			{showPreferences ? '-' : '+'} Tone and style preferences
		</button>

		{#if showPreferences}
			<div class="preference-grid">
				<label class="field">
					<span>Tone</span>
					<select
						value={$briefDraft.preferences.tone}
						onchange={(event) =>
							updatePreferences('tone', (event.currentTarget as HTMLSelectElement).value as Tone)}
					>
						{#each tones as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</label>

				<label class="field">
					<span>Reading level</span>
					<select
						value={$briefDraft.preferences.reading_level}
						onchange={(event) =>
							updatePreferences(
								'reading_level',
								(event.currentTarget as HTMLSelectElement).value as ReadingLevel
							)}
					>
						{#each readingLevels as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</label>

				<label class="field">
					<span>Explanation style</span>
					<select
						value={$briefDraft.preferences.explanation_style}
						onchange={(event) =>
							updatePreferences(
								'explanation_style',
								(event.currentTarget as HTMLSelectElement).value as ExplanationStyle
							)}
					>
						{#each explanationStyles as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</label>

				<label class="field">
					<span>Brevity</span>
					<select
						value={$briefDraft.preferences.brevity}
						onchange={(event) =>
							updatePreferences(
								'brevity',
								(event.currentTarget as HTMLSelectElement).value as Brevity
							)}
					>
						{#each brevityOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</label>
			</div>
		{/if}

		<div class="constraint-row">
			<label class="toggle">
				<input
					type="checkbox"
					checked={$briefDraft.constraints.more_practice}
					onchange={(event) =>
						updateConstraints('more_practice', (event.currentTarget as HTMLInputElement).checked)}
				/>
				<span>Emphasise practice</span>
			</label>

			<label class="toggle">
				<input
					type="checkbox"
					checked={$briefDraft.constraints.keep_short}
					onchange={(event) =>
						updateConstraints('keep_short', (event.currentTarget as HTMLInputElement).checked)}
				/>
				<span>Keep it short</span>
			</label>

			<label class="toggle">
				<input
					type="checkbox"
					checked={$briefDraft.constraints.use_visuals}
					onchange={(event) =>
						updateConstraints('use_visuals', (event.currentTarget as HTMLInputElement).checked)}
				/>
				<span>Include visuals wherever possible</span>
			</label>

			<label class="toggle">
				<input
					type="checkbox"
					checked={$briefDraft.constraints.print_first}
					onchange={(event) =>
						updateConstraints('print_first', (event.currentTarget as HTMLInputElement).checked)}
				/>
				<span>Print first</span>
			</label>
		</div>

		<div class="actions">
			<button class="primary-button" type="submit" disabled={disabled}>
				Build lesson plan
			</button>
		</div>
	</div>
</form>

<style>
	.studio-form {
		display: grid;
	}

	.form-card {
		display: grid;
		gap: 1rem;
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 1.5rem;
		background: rgba(255, 255, 255, 0.82);
		padding: 1.5rem;
	}

	.heading h1,
	.heading p {
		margin: 0;
	}

	.eyebrow {
		margin: 0 0 0.35rem 0;
		font-size: 0.76rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	.lede {
		margin-top: 0.45rem;
		max-width: 60ch;
		color: #625a50;
		line-height: 1.6;
	}

	.notice {
		margin: 0;
		border-radius: 1rem;
		padding: 0.85rem 1rem;
	}

	.notice-error {
		background: rgba(255, 242, 238, 0.94);
		color: #7d3524;
	}

	.field-grid,
	.preference-grid {
		display: grid;
		gap: 0.9rem;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
	}

	.field {
		display: grid;
		gap: 0.4rem;
	}

	.field-wide {
		grid-column: 1 / -1;
	}

	.field span,
	.signal-title {
		font-size: 0.9rem;
		font-weight: 600;
		color: #24343f;
	}

	input,
	textarea,
	select {
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 0.9rem;
		padding: 0.72rem 0.85rem;
		font: inherit;
		background: #f7f4ee;
		color: #1d1b17;
	}

	textarea {
		resize: vertical;
	}

	.toggle-link {
		justify-self: start;
		border: none;
		background: transparent;
		padding: 0;
		color: #35526a;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	.signal-stack {
		display: grid;
		gap: 0.85rem;
	}

	.signal-block {
		display: grid;
		gap: 0.55rem;
		border-radius: 1rem;
		background: #f4f1ea;
		padding: 0.9rem;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.chip {
		border: 0.5px solid rgba(36, 52, 63, 0.16);
		border-radius: 999px;
		background: white;
		padding: 0.35rem 0.8rem;
		font: inherit;
		font-size: 0.84rem;
		color: #57636d;
		cursor: pointer;
	}

	.chip-selected {
		border-color: #1d9e75;
		background: #e1f5ee;
		color: #085041;
	}

	.helper {
		margin: 0;
		font-size: 0.8rem;
		color: #766d63;
	}

	.constraint-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.9rem 1.25rem;
	}

	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		color: #24343f;
	}

	.actions {
		display: flex;
		justify-content: flex-end;
	}

	.primary-button {
		border: none;
		border-radius: 0.95rem;
		background: #1d9e75;
		padding: 0.7rem 1.15rem;
		color: #e1f5ee;
		font: inherit;
		font-weight: 700;
		cursor: pointer;
	}

	.primary-button:disabled {
		cursor: not-allowed;
		opacity: 0.65;
	}

	@media (max-width: 720px) {
		.actions {
			justify-content: stretch;
		}

		.primary-button {
			width: 100%;
		}
	}
</style>
