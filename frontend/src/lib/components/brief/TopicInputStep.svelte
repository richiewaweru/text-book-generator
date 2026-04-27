<script lang="ts">
	interface Props {
		value: string;
		loading?: boolean;
		statusMessage?: string | null;
		onInput: (value: string) => void;
		onSubmit: () => void;
	}

	let {
		value,
		loading = false,
		statusMessage = null,
		onInput,
		onSubmit
	}: Props = $props();
</script>

<form
	class="step-form"
	onsubmit={(event) => {
		event.preventDefault();
		onSubmit();
	}}
>
	<label class="field">
		<span>What are you teaching today?</span>
		<input
			type="text"
			value={value}
			placeholder="Algebra, photosynthesis, main idea..."
			oninput={(event) => onInput((event.currentTarget as HTMLInputElement).value)}
		/>
	</label>

	<p class="helper">
		Start broad. The builder will narrow this into a classroom-ready subtopic.
	</p>

	{#if statusMessage}
		<p class="status" aria-live="polite">{statusMessage}</p>
	{/if}

	<button type="submit" class="primary" disabled={loading || !value.trim()}>
		{loading ? 'Finding subtopics...' : 'Find subtopics'}
	</button>
</form>

<style>
	.step-form {
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

	input {
		border: 1px solid rgba(36, 52, 63, 0.14);
		border-radius: 16px;
		padding: 0.9rem 1rem;
		font: inherit;
		background: #fffdf9;
	}

	.helper,
	.status {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.status {
		color: #085041;
		font-weight: 600;
	}

	.primary {
		justify-self: start;
		border: 0;
		border-radius: 999px;
		background: #1d9e75;
		color: white;
		padding: 0.8rem 1.1rem;
		font-weight: 700;
		cursor: pointer;
	}

	.primary:disabled {
		opacity: 0.6;
		cursor: default;
	}
</style>
