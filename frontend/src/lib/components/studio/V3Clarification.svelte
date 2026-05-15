<script lang="ts">
	import type { V3ClarificationAnswer, V3ClarificationQuestion } from '$lib/types/v3';

	interface Props {
		questions: V3ClarificationQuestion[];
		onAnswered: (answers: V3ClarificationAnswer[]) => void;
	}

	let { questions, onAnswered }: Props = $props();

	let answers = $state<Record<number, string>>({});

	$effect.pre(() => {
		answers = Object.fromEntries(questions.map((_, i) => [i, '']));
	});

	function selectOption(index: number, option: string) {
		answers = { ...answers, [index]: option };
	}

	function skipQuestion(index: number) {
		answers = { ...answers, [index]: '' };
	}

	function canProceed(): boolean {
		return questions.every((q, i) => q.optional || (answers[i]?.trim() ?? '').length > 0);
	}

	function handleSubmit() {
		const result: V3ClarificationAnswer[] = questions.map((q, i) => ({
			question: q.question,
			answer: answers[i]?.trim() ?? ''
		}));
		onAnswered(result);
	}
</script>

<div class="mx-auto max-w-2xl space-y-6 px-4 py-10">
	<header class="space-y-1">
		<p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quick check</p>
		<h2 class="text-2xl font-semibold">One thing before I plan</h2>
	</header>

	{#each questions as q, i}
		<div class="rounded-xl border border-border/60 bg-card p-5 space-y-3">
			<div>
				<p class="text-xs text-muted-foreground mb-1">
					Question {i + 1} of {questions.length}
					{#if q.optional}
						<span class="ml-2 rounded bg-muted px-2 py-0.5 text-xs">optional</span>
					{/if}
				</p>
				<p class="text-sm font-medium">{q.question}</p>
				<p class="mt-1 text-xs text-muted-foreground">{q.reason}</p>
			</div>

			{#if q.answer_type === 'options'}
				<div class="flex flex-wrap gap-2">
					{#each q.options as opt}
						<button
							type="button"
							class="rounded-full border px-4 py-1.5 text-sm transition-colors
								{answers[i] === opt
									? 'border-primary bg-primary/5 font-medium text-primary'
									: 'border-input text-muted-foreground hover:border-primary hover:text-foreground'}"
							onclick={() => selectOption(i, opt)}
						>
							{opt}
						</button>
					{/each}
				</div>
			{:else}
				<textarea
					class="min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
					placeholder={q.optional ? 'Optional — leave blank to skip' : 'Your answer…'}
					bind:value={answers[i]}
				></textarea>
			{/if}

			{#if q.optional && answers[i] !== ''}
				<button
					type="button"
					class="text-xs underline underline-offset-2 text-muted-foreground"
					onclick={() => skipQuestion(i)}
				>
					Skip this
				</button>
			{:else if q.optional}
				<p class="text-xs text-muted-foreground">You can skip this if you're not sure.</p>
			{/if}
		</div>
	{/each}

	<div class="flex gap-3">
		<button
			type="button"
			class="flex-1 rounded-md bg-primary px-4 py-3 text-sm font-semibold
				   text-primary-foreground disabled:opacity-50"
			disabled={!canProceed()}
			onclick={handleSubmit}
		>
			Build the plan →
		</button>
	</div>
</div>
