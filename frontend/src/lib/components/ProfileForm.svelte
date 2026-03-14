<script lang="ts">
	import type { GenerationMode, GenerationRequest, Depth } from '$lib/types';

	let subject = $state('');
	let context = $state('');
	let depth: Depth = $state('standard');
	let mode: GenerationMode = $state('draft');

	interface Props {
		onsubmit: (request: GenerationRequest) => void;
		disabled?: boolean;
	}

	let { onsubmit, disabled = false }: Props = $props();

	function handleSubmit() {
		onsubmit({
			subject,
			context,
			mode,
			depth: mode === 'draft' ? 'survey' : depth
		});
	}
</script>

<form onsubmit={(e: Event) => { e.preventDefault(); handleSubmit(); }} class="generation-form">
	<label>
		Subject
		<input type="text" bind:value={subject} placeholder="e.g. calculus, linear algebra, data structures" required />
	</label>

	<label>
		Context
		<textarea bind:value={context} placeholder="What do you already know about this topic? What specifically confuses you?" required rows="4"></textarea>
	</label>

	<label>
		Mode
		<select bind:value={mode}>
			<option value="draft">Draft (fast first readable version)</option>
			<option value="balanced">Balanced (default full run)</option>
			<option value="strict">Strict (highest polish)</option>
		</select>
	</label>

	<label>
		Depth
		<select bind:value={depth} disabled={mode === 'draft'}>
			<option value="survey">Survey (quick overview)</option>
			<option value="standard">Standard</option>
			<option value="deep">Deep (comprehensive)</option>
		</select>
		{#if mode === 'draft'}
			<span class="hint">Draft mode always uses survey depth for speed.</span>
		{/if}
	</label>

	<button type="submit" {disabled}>Generate Textbook</button>
</form>

<style>
	.generation-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-width: 600px;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
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

	.hint {
		color: #888;
		font-size: 0.8rem;
	}

	input:focus, textarea:focus, select:focus {
		outline: none;
		border-color: #6d9eeb;
	}

	button {
		padding: 0.7rem 1.5rem;
		background: #4a86d6;
		color: #fff;
		border: none;
		border-radius: 6px;
		font-size: 1rem;
		cursor: pointer;
		margin-top: 0.5rem;
	}

	button:hover:not(:disabled) {
		background: #5a96e6;
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
