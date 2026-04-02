<script lang="ts">
	import type { FillInBlankContent } from '../../types';
	import { Card } from '../ui/card';
	import { Badge } from '../ui/badge';
	import { usePrintMode } from '../../utils/printContext';

	let { content }: { content: FillInBlankContent } = $props();

	const getPrintMode = usePrintMode();
	const printMode = $derived(getPrintMode());
</script>

{#if printMode}
	<div class="fill-blank-print">
		{#if content.instruction}
			<p class="fill-blank-print-instruction">{content.instruction}</p>
		{/if}
		<div class="fill-blank-print-passage">
			{#each content.segments as segment}
				{#if segment.is_blank}
					<span class="fill-blank-print-blank">________________</span>
				{:else}
					{segment.text}
				{/if}
			{/each}
		</div>
		{#if content.word_bank?.length}
			<div class="fill-blank-print-word-bank">
				<p class="fill-blank-print-word-bank-label"><strong>Word Bank:</strong></p>
				<div class="fill-blank-print-words">
					{#each content.word_bank as word}
						<span class="fill-blank-print-word">{word}</span>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{:else}
<Card class="border-border/60 p-5 sm:p-6">
	{#if content.instruction}
		<p class="text-sm font-medium leading-relaxed">{content.instruction}</p>
	{/if}

	<div class="mt-3 text-sm leading-loose">
		{#each content.segments as segment}
			{#if segment.is_blank}
				<span
					class="mx-0.5 inline-block min-w-[5rem] border-b-2 border-dashed border-primary/40 px-1 text-center text-transparent"
					title={segment.answer ?? ''}
				>
					{segment.answer ?? '\u00A0\u00A0\u00A0'}
				</span>
			{:else}
				{segment.text}
			{/if}
		{/each}
	</div>

	{#if content.word_bank?.length}
		<div class="mt-4 rounded-lg bg-muted/40 p-3">
			<p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
				Word bank
			</p>
			<div class="mt-2 flex flex-wrap gap-2">
				{#each content.word_bank as word}
					<Badge variant="outline">{word}</Badge>
				{/each}
			</div>
		</div>
	{/if}
</Card>
{/if}

<style>
	.fill-blank-print {
		page-break-inside: avoid;
		margin: 1rem 0;
	}

	.fill-blank-print-instruction {
		font-weight: 500;
		margin-bottom: 0.75rem;
	}

	.fill-blank-print-passage {
		line-height: 2;
		margin-bottom: 1.5rem;
	}

	.fill-blank-print-blank {
		display: inline-block;
		min-width: 4rem;
		border-bottom: 1px solid #000;
		margin: 0 0.25rem;
	}

	.fill-blank-print-word-bank {
		padding: 1rem;
		border: 2px solid #e5e7eb;
		background: #f9fafb;
	}

	.fill-blank-print-word-bank-label {
		margin-bottom: 0.75rem;
	}

	.fill-blank-print-words {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.fill-blank-print-word {
		padding: 0.25rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.25rem;
	}
</style>
