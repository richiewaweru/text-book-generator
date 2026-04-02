<script lang="ts">
	import type { ShortAnswerContent } from '../../types';
	import { Card } from '../ui/card';
	import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../ui/collapsible';
	import { Badge } from '../ui/badge';
	import { usePrintMode } from '../../utils/printContext';
	import RuledLines from '../../print/RuledLines.svelte';

	let { content }: { content: ShortAnswerContent } = $props();

	const getPrintMode = usePrintMode();
	const printMode = $derived(getPrintMode());
	const lines = $derived(content.lines ?? 6);
</script>

{#if printMode}
	<div class="short-answer-print">
		<div class="short-answer-header">
			<span class="short-answer-question">{content.question}</span>
			{#if content.marks}
				<span class="short-answer-marks">[{content.marks} {content.marks === 1 ? 'mark' : 'marks'}]</span>
			{/if}
		</div>
		<RuledLines {lines} label="Answer:" />
	</div>
{:else}
<Card class="border-border/60 p-5 sm:p-6">
	<div class="flex items-start justify-between gap-3">
		<p class="text-sm font-medium leading-relaxed">{content.question}</p>
		{#if content.marks}
			<Badge variant="outline" class="shrink-0">{content.marks} {content.marks === 1 ? 'mark' : 'marks'}</Badge>
		{/if}
	</div>

	<div
		class="mt-3 rounded-lg border border-dashed border-border/80 bg-white/50 p-3"
		style="min-height: {lines * 1.75}rem"
	>
		<p class="text-xs text-muted-foreground/50 italic">Write your answer here...</p>
	</div>

	{#if content.mark_scheme}
		<Collapsible class="mt-3">
			<CollapsibleTrigger
				class="inline-flex h-6 items-center justify-center rounded-xl px-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
			>
				Mark scheme ->
			</CollapsibleTrigger>
			<CollapsibleContent>
				<div class="mt-2 rounded-xl bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
					{content.mark_scheme}
				</div>
			</CollapsibleContent>
		</Collapsible>
	{/if}
</Card>
{/if}

<style>
	.short-answer-print {
		page-break-inside: avoid;
		margin: 1rem 0;
		padding: 1rem;
		border: 1px solid #e5e7eb;
	}

	.short-answer-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 1rem;
	}

	.short-answer-question {
		font-weight: 600;
		flex: 1;
	}

	.short-answer-marks {
		font-size: 0.875rem;
		color: #6b7280;
		margin-left: 1rem;
	}
</style>
