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
	}

	let { onsubmit, disabled = false }: Props = $props();

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

	function addInterest() {
		const tag = interestInput.trim().toLowerCase();
		if (tag && !interests.includes(tag)) {
			interests = [...interests, tag];
		}
		interestInput = '';
	}

	function removeInterest(tag: string) {
		interests = interests.filter((t) => t !== tag);
	}

	function handleInterestKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ',') {
			e.preventDefault();
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

<form onsubmit={(e: Event) => { e.preventDefault(); handleSubmit(); }} class="profile-form">
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

	<button type="submit" class="submit-btn" {disabled}>Complete Setup</button>
</form>

<style>
	.profile-form {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		max-width: 600px;
	}

	.form-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.form-section h3 {
		margin: 0;
		font-size: 1.1rem;
		color: #ddd;
		border-bottom: 1px solid #333;
		padding-bottom: 0.4rem;
	}

	.hint {
		font-size: 0.85rem;
		color: #888;
		margin: 0;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		font-size: 0.9rem;
		color: #ccc;
	}

	input, textarea, select {
		padding: 0.6rem;
		border: 1px solid #444;
		border-radius: 6px;
		background: #1a1a1a;
		color: #eee;
		font-size: 0.95rem;
	}

	input:focus, textarea:focus, select:focus {
		outline: none;
		border-color: #6d9eeb;
	}

	.tag-input-wrapper {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.tag {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.25rem 0.6rem;
		background: #2a3a4a;
		border-radius: 16px;
		font-size: 0.85rem;
		color: #aad;
	}

	.tag-remove {
		background: none;
		border: none;
		color: #888;
		cursor: pointer;
		padding: 0;
		font-size: 1rem;
		line-height: 1;
	}

	.tag-remove:hover {
		color: #e57373;
	}

	.submit-btn {
		padding: 0.75rem 1.5rem;
		background: #4a86d6;
		color: #fff;
		border: none;
		border-radius: 6px;
		font-size: 1rem;
		cursor: pointer;
		margin-top: 0.5rem;
	}

	.submit-btn:hover:not(:disabled) {
		background: #5a96e6;
	}

	.submit-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
