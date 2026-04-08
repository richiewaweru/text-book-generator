<script lang="ts">
	import type { WhatNextContent } from '../../types';
	import { Card } from '../ui/card';
	import { renderInlineMarkdown } from '../../markdown';

	let { content }: { content: WhatNextContent } = $props();
</script>

<Card class="border-l-4 border-l-amber-400 bg-amber-50/65 p-6">
	<div class="space-y-3">
		<p class="eyebrow text-amber-600">What next</p>
		<p class="text-sm leading-7 text-foreground/80">{@html renderInlineMarkdown(content.body)}</p>
		{#if content.prerequisites?.length}
			<p class="text-xs text-muted-foreground">
				<span class="font-semibold">Prerequisites:</span>
				{content.prerequisites.join(' | ')}
			</p>
		{/if}
		<p class="text-sm font-semibold font-serif text-amber-700">{content.next} -></p>
	</div>
</Card>
