<script lang="ts">
	import type { V3ClarificationAnswer, V3ClarificationQuestion } from '$lib/types/v3';

	interface Props {
		questions: V3ClarificationQuestion[];
		onAnswered: (answers: V3ClarificationAnswer[]) => void;
	}

	let { questions, onAnswered }: Props = $props();

	let answers = $state<string[]>([]);

	$effect.pre(() => {
		answers = questions.map(() => '');
	});

	const allAnswered = $derived(
		questions.every((q, i) => q.optional || answers[i]?.trim().length > 0)
	);

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (!allAnswered) return;
		const result: V3ClarificationAnswer[] = questions.map((q, i) => ({
			question: q.question,
			answer: answers[i]?.trim() ?? ''
		}));
		onAnswered(result);
	}
</script>

<div class="mx-auto max-w-xl space-y-6 px-4 py-10">
	<h2 class="text-2xl font-semibold">Just a couple of things</h2>
	<form class="space-y-5" onsubmit={handleSubmit}>
		{#each questions as q, i}
			<div class="grid gap-2">
				<label class="text-sm font-medium" for="clarify-{i}">{q.question}</label>
				{#if q.reason}
					<p class="text-xs text-muted-foreground">{q.reason}</p>
				{/if}
				<input
					id="clarify-{i}"
					type="text"
					class="rounded-md border border-input bg-background px-3 py-2"
					bind:value={answers[i]}
					placeholder={q.optional ? 'Optional' : 'Your answer'}
				/>
			</div>
		{/each}
		<button
			type="submit"
			disabled={!allAnswered}
			class="w-full rounded-md bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
		>
			Continue
		</button>
	</form>
</div>
