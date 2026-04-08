<script lang="ts">
	import type { SummaryBlockContent } from '../../types';
	import { Card } from '../ui/card';
	import { renderInlineMarkdown } from '../../markdown';

	let { content }: { content: SummaryBlockContent } = $props();
</script>

<Card class="border-primary/10 bg-muted/40 p-5 sm:p-6">
	<h3 class="text-sm font-semibold uppercase tracking-[0.14em] text-muted-foreground">
		{content.heading ?? 'In summary'}
	</h3>
	<ul class="mt-3 list-disc list-inside space-y-1.5 text-sm leading-relaxed">
		{#each content.items as item}
			<li>{@html renderInlineMarkdown(item.text)}</li>
		{/each}
	</ul>
	{#if content.closing}
		<p class="mt-3 text-sm leading-relaxed text-muted-foreground">
			{@html renderInlineMarkdown(content.closing)}
		</p>
	{/if}
</Card>
