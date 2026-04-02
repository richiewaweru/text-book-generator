<script lang="ts">
	import type { QuizContent } from '../../types';
	import { Card } from '../ui/card';
	import { Button } from '../ui/button';
	import { CircleCheck, CircleX, RotateCcw } from 'lucide-svelte';
	import { usePrintMode } from '../../utils/printContext';
	import AnswerMarker from '../../print/AnswerMarker.svelte';

	let { content, showAnswersInPrint = true }: { content: QuizContent; showAnswersInPrint?: boolean } = $props();

	let selected = $state<number | null>(null);
	let submitted = $state(false);

	const getPrintMode = usePrintMode();
	const printMode = $derived(getPrintMode());

	function select(index: number) {
		if (submitted) return;
		selected = index;
		submitted = true;
	}

	function reset() {
		selected = null;
		submitted = false;
	}

	const isCorrect = $derived(selected !== null && Boolean(content.options[selected]?.correct));
</script>

{#if printMode}
	<div class="quiz-print">
		<div class="quiz-print-question">{content.question}</div>
		<div class="quiz-print-options">
			{#each content.options as option, idx}
				<div class="quiz-print-option">
					<span class="quiz-print-letter">{String.fromCharCode(65 + idx)}.</span>
					<span class="quiz-print-text">{option.text}</span>
					<AnswerMarker isCorrect={option.correct} showAnswers={showAnswersInPrint} />
				</div>
			{/each}
		</div>
		{#if showAnswersInPrint}
			{@const correctOption = content.options.find((o) => o.correct)}
			{#if correctOption?.explanation}
				<div class="quiz-print-explanation">
					<strong>Explanation:</strong>
					<span>{correctOption.explanation}</span>
				</div>
			{/if}
		{/if}
	</div>
{:else}
<Card class="border-primary/10 bg-white/85 p-6">
	<div class="space-y-4">
		<div class="space-y-2">
			<p class="eyebrow text-emerald-600">Quiz</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">Quick concept check</h3>
			<p class="text-base leading-7 text-foreground/84">{content.question}</p>
		</div>

		<div class="space-y-2">
			{#each content.options as option, i}
				{@const isSelected = selected === i}
				{@const showResult = submitted && isSelected}
				<button
					class="w-full cursor-pointer rounded-[1rem] border bg-white/80 p-4 text-left text-sm transition-colors
						{submitted
							? isSelected
								? option.correct
									? 'border-emerald-300 bg-emerald-50/75'
									: 'border-amber-300 bg-amber-50/75'
								: option.correct
									? 'border-emerald-200 bg-emerald-50/55'
									: 'border-border/70 opacity-65'
							: 'border-border/70 hover:border-emerald-200 hover:bg-emerald-50/40'}"
					onclick={() => select(i)}
					disabled={submitted}
				>
					<div class="flex items-start gap-3">
						{#if showResult}
							{#if option.correct}
								<CircleCheck class="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
							{:else}
								<CircleX class="mt-1 h-4 w-4 shrink-0 text-amber-600" />
							{/if}
						{:else if submitted && option.correct}
							<CircleCheck class="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
						{:else}
							<div class="mt-1 h-4 w-4 shrink-0 rounded-full border-2 border-muted-foreground/30"></div>
						{/if}

						<div class="space-y-2">
							<p class="text-sm font-semibold text-foreground/88">{option.text}</p>
							{#if submitted && content.show_explanations !== false}
								<p class="text-sm leading-6 text-muted-foreground">{option.explanation}</p>
							{/if}
						</div>
					</div>
				</button>
			{/each}
		</div>

		{#if submitted}
			{#if isCorrect}
				<div class="rounded-[1rem] bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">
					<p class="font-semibold">Correct!</p>
					<p class="mt-1">{content.feedback_correct}</p>
				</div>
			{:else}
				<div class="rounded-[1rem] bg-amber-50 p-4">
					<div class="flex items-start gap-2">
						<CircleX class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
						<div class="flex-1">
							<p class="text-sm font-semibold text-amber-900">Not quite!</p>
							<p class="mt-1 text-sm leading-6 text-amber-900/85">
								{content.feedback_incorrect}
							</p>
						</div>
					</div>
					<div class="mt-3 flex justify-end">
						<Button variant="outline" size="sm" class="gap-1.5 text-xs" onclick={reset}>
							<RotateCcw class="h-3 w-3" />
							Try again
						</Button>
					</div>
				</div>
			{/if}
		{/if}
	</div>
</Card>
{/if}

<style>
	.quiz-print {
		page-break-inside: avoid;
		margin: 1rem 0;
		padding: 1rem;
		border: 2px solid #e5e7eb;
	}

	.quiz-print-question {
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.quiz-print-options {
		margin-bottom: 1rem;
	}

	.quiz-print-option {
		display: flex;
		align-items: baseline;
		margin-bottom: 0.5rem;
	}

	.quiz-print-letter {
		font-weight: 600;
		margin-right: 0.5rem;
		min-width: 1.5rem;
	}

	.quiz-print-text {
		flex: 1;
	}

	.quiz-print-explanation {
		border-top: 1px solid #d1d5db;
		padding-top: 0.75rem;
		margin-top: 0.75rem;
		font-size: 0.875rem;
	}
</style>
