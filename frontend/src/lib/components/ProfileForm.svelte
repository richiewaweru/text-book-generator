<script lang="ts">
	import type { GenerationRequest, Depth, NotationLanguage } from '$lib/types';

	let subject = $state('');
	let age = $state(16);
	let context = $state('');
	let depth: Depth = $state('standard');
	let language: NotationLanguage = $state('plain');

	interface Props {
		onsubmit: (request: GenerationRequest) => void;
		disabled?: boolean;
	}

	let { onsubmit, disabled = false }: Props = $props();

	function handleSubmit() {
		onsubmit({ subject, age, context, depth, language });
	}
</script>

<form onsubmit={(e: Event) => { e.preventDefault(); handleSubmit(); }}>
	<label>
		Subject
		<input type="text" bind:value={subject} placeholder="e.g. calculus, linear algebra" required />
	</label>

	<label>
		Age
		<input type="number" bind:value={age} min="8" max="99" required />
	</label>

	<label>
		Context
		<textarea bind:value={context} placeholder="What do you already know? What confuses you?" required></textarea>
	</label>

	<label>
		Depth
		<select bind:value={depth}>
			<option value="survey">Survey</option>
			<option value="standard">Standard</option>
			<option value="deep">Deep</option>
		</select>
	</label>

	<label>
		Notation
		<select bind:value={language}>
			<option value="plain">Plain English</option>
			<option value="math_notation">Math Notation</option>
			<option value="python">Python</option>
			<option value="pseudocode">Pseudocode</option>
		</select>
	</label>

	<button type="submit" {disabled}>Generate Textbook</button>
</form>
