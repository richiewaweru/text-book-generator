<script lang="ts">
	import type { PracticeContent } from '../../types';
	import { Card } from '../ui/card';
	import { usePrintMode } from '../../utils/printContext';
	import RuledLines from '../../print/RuledLines.svelte';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent
	} from '../ui/accordion';
	import { Badge } from '../ui/badge';
	import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../ui/collapsible';
	import { Button } from '../ui/button';

	type PracticeStackMode = 'accordion' | 'flat-list';
	type SelfAssessment = 'matched' | 'review';

	let {
		content,
		mode = 'accordion'
	}: { content: PracticeContent; mode?: PracticeStackMode } = $props();

	const difficultyConfig: Record<string, { label: string; className: string }> = {
		warm: { label: 'Warm', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
		medium: { label: 'Medium', className: 'bg-amber-50 text-amber-700 border-amber-200' },
		cold: { label: 'Cold', className: 'bg-blue-50 text-blue-700 border-blue-200' },
		extension: { label: 'Extension', className: 'bg-purple-50 text-purple-700 border-purple-200' }
	};

	const getPrintMode = usePrintMode();
	const printMode = $derived(getPrintMode());

	let hintsRevealed = $state<Record<number, number>>({});
	let selfAssessments = $state<Record<number, SelfAssessment>>({});

	function revealNextHint(index: number, total: number) {
		const current = hintsRevealed[index] ?? 0;
		if (current < total) {
			hintsRevealed[index] = current + 1;
		}
	}

	function setAssessment(index: number, value: SelfAssessment) {
		selfAssessments[index] = value;
	}
</script>

{#if printMode}
	<div class="practice-print">
		<h4 class="practice-print-title">{content.label ?? 'Practice problems'}</h4>
		{#each content.problems as problem, idx}
			<div class="practice-print-problem">
				<div class="practice-print-header">
					<span class="practice-print-number">Problem {idx + 1}</span>
					<span class="practice-print-difficulty">{problem.difficulty}</span>
				</div>
				{#if problem.context}
					<p class="practice-print-context">{problem.context}</p>
				{/if}
				<p class="practice-print-question">{problem.question}</p>
				{#if problem.hints?.length}
					<div class="practice-print-hints">
						<p class="practice-print-hints-label"><strong>Hints:</strong></p>
						{#each problem.hints as hint}
							<p class="practice-print-hint">• {hint.text}</p>
						{/each}
					</div>
				{/if}
				{#if problem.writein_lines && problem.writein_lines > 0}
					<RuledLines lines={problem.writein_lines} label="Your answer:" />
				{/if}
				{#if problem.solution && content.solutions_available}
					<div class="practice-print-solution">
						<p><strong>Solution:</strong> {problem.solution.approach}</p>
						<p class="practice-print-answer"><strong>Answer:</strong> {problem.solution.answer}</p>
					</div>
				{/if}
			</div>
		{/each}
	</div>
{:else}
<Card class="border-primary/10 bg-white/88 p-6">
	<div class="space-y-4">
		<div class="space-y-2">
			<p class="eyebrow text-amber-600">{content.label ?? 'Practice problems'}</p>
			<p class="text-sm leading-6 text-muted-foreground">
				{mode === 'accordion'
					? 'Open one problem at a time, reveal hints progressively, and only expand the worked solution if it is needed.'
					: 'Keep every problem visible, reveal hints progressively, and check your own work without losing your place.'}
			</p>
		</div>

		{#snippet problemBody(problem: PracticeContent['problems'][number], index: number)}
			{@const shown = hintsRevealed[index] ?? 0}
			{@const assessment = selfAssessments[index]}

			{#if problem.context}
				<div class="rounded-xl bg-muted/45 p-3 text-sm leading-6 text-muted-foreground">
					Context: {problem.context}
				</div>
			{/if}

			<div class="space-y-3">
				{#each problem.hints.slice(0, shown) as hint}
					<div class="rounded-xl bg-muted/55 p-3 text-sm leading-relaxed text-muted-foreground">
						<p class="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-foreground/60">
							Hint {hint.level} of {problem.hints.length}
						</p>
						<p>{hint.text}</p>
					</div>
				{/each}

				{#if shown < problem.hints.length}
					<Button
						variant="ghost"
						size="sm"
						class="h-7 px-0 text-xs text-muted-foreground"
						onclick={() => revealNextHint(index, problem.hints.length)}
					>
						{shown === 0 ? 'Show hint' : 'Show next hint'}
					</Button>
				{/if}
			</div>

			{#if problem.solution}
				<Collapsible class="mt-2">
					<CollapsibleTrigger
						class="inline-flex h-7 items-center justify-center rounded-xl px-0 text-xs font-medium text-emerald-700 transition-colors hover:bg-accent hover:text-emerald-800"
					>
						Show answer
					</CollapsibleTrigger>
					<CollapsibleContent>
						<div class="mt-2 rounded-xl bg-emerald-50 p-3 text-sm font-medium leading-relaxed text-emerald-800">
							{problem.solution.answer}
						</div>

						<Collapsible class="mt-2">
							<CollapsibleTrigger
								class="inline-flex h-7 items-center justify-center rounded-xl px-0 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
							>
								Show worked solution
							</CollapsibleTrigger>
							<CollapsibleContent>
								<div class="mt-2 rounded-xl bg-muted/50 p-3 text-sm leading-relaxed text-muted-foreground">
									<p class="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-foreground/60">
										Approach
									</p>
									<p>{problem.solution.approach}</p>
									{#if problem.solution.worked}
										<p class="mt-3">{problem.solution.worked}</p>
									{/if}
								</div>
							</CollapsibleContent>
						</Collapsible>
					</CollapsibleContent>
				</Collapsible>
			{/if}

			{#if problem.self_assess}
				<div class="rounded-xl border border-border/70 bg-background/80 p-4">
					<p class="text-sm font-semibold text-primary">Self-check</p>
					<p class="mt-1 text-sm leading-6 text-muted-foreground">
						Compare your work to the answer and mark how it went.
					</p>
					<div class="mt-3 flex flex-wrap gap-2">
						<Button
							variant={assessment === 'matched' ? 'default' : 'outline'}
							size="sm"
							onclick={() => setAssessment(index, 'matched')}
						>
							Matched
						</Button>
						<Button
							variant={assessment === 'review' ? 'default' : 'outline'}
							size="sm"
							onclick={() => setAssessment(index, 'review')}
						>
							Needs review
						</Button>
					</div>
				</div>
			{/if}

			{#if problem.writein_lines && problem.writein_lines > 0}
				<div class="space-y-3 rounded-xl border border-dashed border-border/80 bg-background/70 p-4">
					{#each Array.from({ length: problem.writein_lines }) as _}
						<div class="h-6 border-b border-border/70"></div>
					{/each}
				</div>
			{/if}
		{/snippet}

		{#if mode === 'accordion'}
			<Accordion type="single" class="space-y-2">
				{#each content.problems as problem, i}
					{@const diff = difficultyConfig[problem.difficulty] ?? difficultyConfig.medium}
					<AccordionItem value={`problem-${i}`} class="rounded-xl border bg-card px-4">
						<AccordionTrigger class="py-4 hover:no-underline">
							<div class="flex items-start gap-3 text-left">
								<Badge variant="outline" class={diff.className}>{diff.label}</Badge>
								<div>
									{#if problem.context}
										<div class="mb-1 text-xs italic text-muted-foreground">{problem.context}</div>
									{/if}
									<span class="text-sm leading-relaxed">{problem.question}</span>
								</div>
							</div>
						</AccordionTrigger>

						<AccordionContent class="space-y-4 pb-4">
							{@render problemBody(problem, i)}
						</AccordionContent>
					</AccordionItem>
				{/each}
			</Accordion>
		{:else}
			<div class="space-y-4">
				{#each content.problems as problem, i}
					{@const diff = difficultyConfig[problem.difficulty] ?? difficultyConfig.medium}
					<div class="rounded-xl border bg-card p-4">
						<div class="mb-4 flex items-start gap-3">
							<Badge variant="outline" class={diff.className}>{diff.label}</Badge>
							<div>
								{#if problem.context}
									<div class="mb-1 text-xs italic text-muted-foreground">{problem.context}</div>
								{/if}
								<p class="text-sm leading-relaxed">{problem.question}</p>
							</div>
						</div>

						<div class="space-y-4">
							{@render problemBody(problem, i)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</Card>
{/if}

<style>
	.practice-print {
		margin: 1rem 0;
	}

	.practice-print-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.practice-print-problem {
		page-break-inside: avoid;
		margin-bottom: 2rem;
		padding: 1rem;
		border: 1px solid #e5e7eb;
	}

	.practice-print-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}

	.practice-print-number {
		font-weight: 600;
	}

	.practice-print-difficulty {
		font-size: 0.875rem;
		color: #6b7280;
		text-transform: capitalize;
	}

	.practice-print-context {
		font-size: 0.875rem;
		font-style: italic;
		color: #6b7280;
		margin-bottom: 0.5rem;
	}

	.practice-print-question {
		margin-bottom: 1rem;
		line-height: 1.6;
	}

	.practice-print-hints {
		background: #f9fafb;
		padding: 0.75rem;
		margin: 1rem 0;
		border-left: 3px solid #d1d5db;
	}

	.practice-print-hints-label {
		margin-bottom: 0.5rem;
	}

	.practice-print-hint {
		margin: 0.25rem 0;
		font-size: 0.875rem;
	}

	.practice-print-solution {
		border-top: 1px solid #d1d5db;
		padding-top: 0.75rem;
		margin-top: 1rem;
	}

	.practice-print-answer {
		margin-top: 0.5rem;
	}
</style>
