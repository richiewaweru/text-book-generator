<script lang="ts">
	import type {
		ProfileCreateRequest,
		EducationLevel,
		LearningStyle,
		NotationLanguage,
		Depth
	} from '$lib/types';

	interface Props {
		onsubmit: (data: ProfileCreateRequest) => void;
		disabled?: boolean;
		initialData?: ProfileCreateRequest | null;
		submitLabel?: string;
	}

	let {
		onsubmit,
		disabled = false,
		initialData = null,
		submitLabel = 'Complete Setup'
	}: Props = $props();

	let age = $state(16);
	let educationLevel: EducationLevel = $state('high_school');
	let learningStyle: LearningStyle = $state('reading_writing');
	let preferredNotation: NotationLanguage = $state('plain');
	let preferredDepth: Depth = $state('standard');
	let priorKnowledge = $state('');
	let goals = $state('');
	let learnerDescription = $state('');
	let interests: string[] = $state([]);
	let interestInput = $state('');
	let initializedFromProps = $state(false);

	$effect(() => {
		if (!initialData || initializedFromProps) {
			return;
		}

		age = initialData.age;
		educationLevel = initialData.education_level;
		learningStyle = initialData.learning_style;
		preferredNotation = initialData.preferred_notation;
		preferredDepth = initialData.preferred_depth;
		priorKnowledge = initialData.prior_knowledge;
		goals = initialData.goals;
		learnerDescription = initialData.learner_description;
		interests = [...initialData.interests];
		initializedFromProps = true;
	});

	function addInterest() {
		const tag = interestInput.trim().toLowerCase();
		if (tag && !interests.includes(tag)) {
			interests = [...interests, tag];
		}
		interestInput = '';
	}

	function removeInterest(tag: string) {
		interests = interests.filter((entry) => entry !== tag);
	}

	function handleInterestKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			addInterest();
		}
	}

	function handleSubmit() {
		onsubmit({
			age,
			education_level: educationLevel,
			interests,
			learning_style: learningStyle,
			preferred_notation: preferredNotation,
			prior_knowledge: priorKnowledge,
			goals,
			preferred_depth: preferredDepth,
			learner_description: learnerDescription
		});
	}
</script>

<form onsubmit={(event: Event) => { event.preventDefault(); handleSubmit(); }} class="profile-form">
	<div class="form-section">
		<h3>About You</h3>

		<label>
			Age
			<input type="number" bind:value={age} min="8" max="99" required />
		</label>

		<label>
			Education Level
			<select bind:value={educationLevel}>
				<option value="elementary">Elementary School</option>
				<option value="middle_school">Middle School</option>
				<option value="high_school">High School</option>
				<option value="undergraduate">Undergraduate</option>
				<option value="graduate">Graduate</option>
				<option value="professional">Professional</option>
			</select>
		</label>
	</div>

	<div class="form-section">
		<h3>Learning Preferences</h3>

		<label>
			How do you learn best?
			<select bind:value={learningStyle}>
				<option value="visual">Visual (diagrams, charts, images)</option>
				<option value="reading_writing">Reading & Writing (text, notes)</option>
				<option value="kinesthetic">Hands-on (exercises, experiments)</option>
				<option value="auditory">Auditory (explanations, discussions)</option>
			</select>
		</label>

		<label>
			Preferred Notation
			<select bind:value={preferredNotation}>
				<option value="plain">Plain English</option>
				<option value="math_notation">Math Notation</option>
				<option value="python">Python</option>
				<option value="pseudocode">Pseudocode</option>
			</select>
		</label>

		<label>
			Default Depth
			<select bind:value={preferredDepth}>
				<option value="survey">Survey (quick overview)</option>
				<option value="standard">Standard</option>
				<option value="deep">Deep (comprehensive)</option>
			</select>
		</label>
	</div>

	<div class="form-section">
		<h3>Interests</h3>
		<p class="hint">Add topics you're interested in. These help personalize examples and analogies.</p>

		<div class="tag-input-wrapper">
			<div class="tags">
				{#each interests as tag}
					<span class="tag">
						{tag}
						<button type="button" class="tag-remove" onclick={() => removeInterest(tag)}>&times;</button>
					</span>
				{/each}
			</div>
			<input
				type="text"
				bind:value={interestInput}
				onkeydown={handleInterestKeydown}
				placeholder="Type an interest and press Enter"
			/>
		</div>
	</div>

	<div class="form-section">
		<h3>Background</h3>

		<label>
			What do you already know? (optional)
			<textarea bind:value={priorKnowledge} placeholder="e.g. I'm comfortable with algebra and basic geometry..." rows="3"></textarea>
		</label>

		<label>
			What are your learning goals? (optional)
			<textarea bind:value={goals} placeholder="e.g. I want to understand calculus well enough for college entrance exams..." rows="3"></textarea>
		</label>

		<label>
			Learner description (optional)
			<textarea bind:value={learnerDescription} placeholder="Describe your learning abilities, gaps, or any signals that might help personalise content. e.g. I struggle with abstract concepts but do well with concrete examples..." rows="4"></textarea>
			<span class="hint">This will be replaced by automated diagnostics in a future version.</span>
		</label>
	</div>

	<button type="submit" class="submit-btn" {disabled}>{submitLabel}</button>
</form>

<style>
	.profile-form {
		display: flex;
		flex-direction: column;
		gap: 2rem;
		max-width: 680px;
	}

	.form-section {
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.form-section h3 {
		margin: 0;
		font-size: 1.2rem;
		font-weight: 700;
		letter-spacing: 0.01em;
		color: #1f2b34;
		border-bottom: 1px solid rgba(61, 47, 26, 0.25);
		padding-bottom: 0.55rem;
	}

	.hint {
		font-size: 0.92rem;
		line-height: 1.55;
		color: #5c554c;
		margin: 0;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		font-size: 0.96rem;
		font-weight: 600;
		line-height: 1.4;
		color: #2b241d;
	}

	input, textarea, select {
		width: 100%;
		box-sizing: border-box;
		padding: 0.9rem 1rem;
		border: 1px solid rgba(53, 71, 86, 0.22);
		border-radius: 12px;
		background: rgba(255, 252, 247, 0.96);
		color: #1f2b34;
		font: inherit;
		font-weight: 500;
		line-height: 1.5;
		box-shadow:
			0 1px 0 rgba(255, 255, 255, 0.8) inset,
			0 10px 24px rgba(57, 44, 29, 0.05);
		transition:
			border-color 140ms ease,
			box-shadow 140ms ease,
			background-color 140ms ease;
	}

	input:focus, textarea:focus, select:focus {
		outline: none;
		border-color: rgba(54, 101, 130, 0.58);
		box-shadow:
			0 0 0 4px rgba(84, 135, 171, 0.16),
			0 12px 28px rgba(57, 44, 29, 0.08);
		background: #fffdf9;
	}

	input::placeholder,
	textarea::placeholder {
		color: #7a7167;
		font-weight: 400;
	}

	select {
		appearance: auto;
	}

	textarea {
		min-height: 7.5rem;
		resize: vertical;
	}

	.tag-input-wrapper {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.tag {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.45rem 0.75rem;
		background: rgba(54, 101, 130, 0.1);
		border: 1px solid rgba(54, 101, 130, 0.14);
		border-radius: 999px;
		font-size: 0.88rem;
		font-weight: 600;
		color: #2b5067;
	}

	.tag-remove {
		background: none;
		border: none;
		color: #5c554c;
		cursor: pointer;
		padding: 0;
		font-size: 1rem;
		line-height: 1;
	}

	.tag-remove:hover {
		color: #e57373;
	}

	.tag-remove:focus-visible {
		outline: 2px solid rgba(84, 135, 171, 0.35);
		outline-offset: 3px;
		border-radius: 999px;
	}

	.submit-btn {
		align-self: flex-start;
		padding: 0.95rem 1.6rem;
		background: linear-gradient(135deg, #244560, #3f7598);
		color: #fff;
		border: none;
		border-radius: 999px;
		font-size: 1rem;
		font-weight: 700;
		letter-spacing: 0.01em;
		cursor: pointer;
		margin-top: 0.25rem;
		box-shadow: 0 16px 32px rgba(31, 61, 82, 0.2);
		transition:
			transform 140ms ease,
			box-shadow 140ms ease,
			filter 140ms ease;
	}

	.submit-btn:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 18px 36px rgba(31, 61, 82, 0.24);
		filter: brightness(1.04);
	}

	.submit-btn:focus-visible {
		outline: 3px solid rgba(84, 135, 171, 0.25);
		outline-offset: 3px;
	}

	.submit-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		box-shadow: none;
	}

	@media (max-width: 640px) {
		.profile-form {
			gap: 1.75rem;
		}

		input, textarea, select {
			padding: 0.85rem 0.9rem;
		}

		.submit-btn {
			width: 100%;
			justify-content: center;
		}
	}
</style>
