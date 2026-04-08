<script lang="ts">
	import type { KeyFactContent } from '../../types';
	import { Card } from '../ui/card';

	let { content }: { content: KeyFactContent } = $props();
</script>

<Card class="border-primary/15 bg-primary/4 p-5 sm:p-6">
	<p class="text-2xl font-semibold leading-tight font-serif text-foreground">
		{content.fact}
	</p>
	{#if content.context}
		<p class="mt-2 text-sm leading-relaxed text-muted-foreground">
			{content.context}
		</p>
	{/if}
	{#if content.source}
		<p class="mt-1 text-xs text-muted-foreground/70">
			Source: {content.source}
		</p>
	{/if}
</Card>
