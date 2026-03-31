<script lang="ts">
	import type { FillInBlankContent } from '../../types';
	import { Card } from '../ui/card';
	import { Badge } from '../ui/badge';

	let { content }: { content: FillInBlankContent } = $props();
</script>

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
