<script lang="ts">
	import type { PitfallContent } from '../../types';
	import { Alert, AlertTitle, AlertDescription } from '../ui/alert';
	import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../ui/collapsible';
	import { TriangleAlert } from 'lucide-svelte';
	import { renderInlineMarkdown } from '../../markdown';

	let { content }: { content: PitfallContent } = $props();

	const displayExamples = $derived(content.examples ?? (content.example ? [content.example] : []));
	const isMinor = $derived(content.severity === 'minor');
</script>

<div class="pitfall-alert-root">
<Alert class={isMinor ? 'border-amber-200 bg-amber-50/60' : 'border-orange-200 bg-orange-50/80'}>
	<TriangleAlert class="h-4 w-4 {isMinor ? 'text-amber-500' : 'text-orange-600'}" />
	<AlertTitle class="{isMinor ? 'text-amber-700' : 'text-orange-700'} text-sm font-semibold">
		Common Pitfall - {content.misconception}
	</AlertTitle>

	{#if content.why}
		<p class="mt-1 text-xs italic text-orange-600/80">
			Why students think this: {@html renderInlineMarkdown(content.why)}
		</p>
	{/if}

	<AlertDescription class="mt-1 text-sm leading-relaxed">
		{@html renderInlineMarkdown(content.correction)}
	</AlertDescription>

	{#if displayExamples.length > 0}
		<Collapsible class="mt-2">
			<CollapsibleTrigger
				class="inline-flex h-6 items-center justify-center rounded-xl px-2 text-xs font-medium text-orange-600 transition-colors hover:bg-accent hover:text-orange-700"
			>
				{displayExamples.length === 1 ? 'See example' : `See examples (${displayExamples.length})`} ->
			</CollapsibleTrigger>
			<CollapsibleContent>
				<div class="mt-2 space-y-2">
					{#each displayExamples as example}
						<div class="rounded-xl bg-white/70 p-2 text-xs italic text-muted-foreground">
							{@html renderInlineMarkdown(example)}
						</div>
					{/each}
				</div>
			</CollapsibleContent>
		</Collapsible>
	{/if}
</Alert>
</div>

<style>
	@media print {
		.pitfall-alert-root {
			page-break-inside: avoid;
			border-left: 3px solid #d97706;
			padding-left: 0.75rem;
			margin: 1rem 0;
		}
	}
</style>

