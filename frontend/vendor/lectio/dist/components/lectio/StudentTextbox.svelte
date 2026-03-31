<script lang="ts">
	import type { StudentTextboxContent } from '../../types';
	import { Card } from '../ui/card';

	let { content }: { content: StudentTextboxContent } = $props();

	const lines = $derived(content.lines ?? 4);
</script>

<Card class="border-border/60 p-5 sm:p-6">
	{#if content.label}
		<p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
			{content.label}
		</p>
	{/if}
	<p class="mt-1 text-sm leading-relaxed">{content.prompt}</p>
	<div
		class="mt-3 rounded-lg border border-dashed border-border/80 bg-white/50 p-3"
		style="min-height: {lines * 1.75}rem"
	>
		<p class="text-xs text-muted-foreground/50 italic">Write your answer here...</p>
	</div>
</Card>
