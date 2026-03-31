<script lang="ts">
	import type { DefinitionContent } from '../../types';
	import { Card } from '../ui/card';
	import { Button } from '../ui/button';
	import { Badge } from '../ui/badge';
	import { ChevronRight } from 'lucide-svelte';
	import MathFormula from './MathFormula.svelte';

	let { content }: { content: DefinitionContent } = $props();
	let showFormal = $state(false);
</script>

<Card class="border-l-4 border-l-fuchsia-500 bg-fuchsia-50/65">
	<div class="space-y-4 p-6">
		<div class="space-y-2">
			<p class="eyebrow text-fuchsia-600">Define</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.term}</h3>
		</div>

		<div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
			<p class="text-base leading-7 text-foreground/85">
				{showFormal ? content.formal : content.plain}
			</p>

			{#if content.symbol}
				<div class="rounded-[1.25rem] border border-fuchsia-200 bg-white/88 px-4 py-3 text-center text-3xl font-semibold text-fuchsia-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
					{content.symbol}
				</div>
			{/if}
		</div>

		<Button
			variant="ghost"
			size="sm"
			onclick={() => (showFormal = !showFormal)}
			class="w-fit px-0 text-fuchsia-700 hover:bg-transparent hover:text-fuchsia-800"
		>
			{showFormal ? 'Show plain language' : 'Show formal definition'}
			<ChevronRight class="h-4 w-4 transition-transform {showFormal ? 'rotate-90' : ''}" />
		</Button>

		{#if content.etymology}
			<p class="text-sm italic text-muted-foreground">Etymology: {content.etymology}</p>
		{/if}

		{#if content.notation}
			<div class="rounded-[1.25rem] border border-fuchsia-200 bg-white/85 p-4">
				<p class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-fuchsia-700/80">
					Notation
				</p>
				<MathFormula formula={content.notation} displayMode class="text-lg text-primary" />
			</div>
		{/if}

		{#if content.examples?.length}
			<div class="space-y-2">
				<p class="text-xs font-semibold uppercase tracking-[0.18em] text-fuchsia-700/80">
					Usage examples
				</p>
				<ul class="space-y-1">
					{#each content.examples as example}
						<li class="text-sm italic text-muted-foreground">
							"{example.replace(/^"|"$/g, '')}"
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if content.related_terms?.length}
			<div class="flex flex-wrap gap-2">
				{#each content.related_terms as term}
					<Badge variant="outline" class="border-fuchsia-200 bg-white/80 text-fuchsia-700">
						{term}
					</Badge>
				{/each}
			</div>
		{/if}
	</div>
</Card>
