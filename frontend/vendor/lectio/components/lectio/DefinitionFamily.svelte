<script lang="ts">
	import type { DefinitionFamilyContent } from '../../types';
	import { Card } from '../ui/card';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent
	} from '../ui/accordion';
	import DefinitionCard from './DefinitionCard.svelte';

	let { content }: { content: DefinitionFamilyContent } = $props();
</script>

<Card class="overflow-hidden border-fuchsia-200 bg-[linear-gradient(180deg,rgba(253,244,255,0.9),rgba(255,255,255,0.92))] shadow-[0_20px_48px_rgba(192,38,211,0.1)]">
	<div class="space-y-4 p-6">
		<div class="space-y-2">
			<p class="eyebrow text-fuchsia-600">Definition family</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.family_title}</h3>
			{#if content.family_intro}
				<p class="text-sm leading-6 text-muted-foreground">{content.family_intro}</p>
			{/if}
		</div>

		<Accordion type="single" class="space-y-3">
			{#each content.definitions as definition, index}
				<AccordionItem
					value={`definition-${index}`}
					class="overflow-hidden rounded-[1.55rem] border border-fuchsia-200/70 bg-white/84 shadow-[0_14px_36px_rgba(15,23,42,0.08)]"
				>
					<AccordionTrigger class="px-5">
						<div class="flex flex-col items-start gap-1 text-left">
							<span class="font-semibold text-foreground/92">{definition.term}</span>
							{#if definition.symbol}
								<span class="text-sm text-fuchsia-700/78">{definition.symbol}</span>
							{/if}
						</div>
					</AccordionTrigger>
					<AccordionContent>
						<div class="rounded-[1.4rem] bg-[linear-gradient(180deg,rgba(253,244,255,0.72),rgba(255,255,255,0.95))] p-1">
							<DefinitionCard content={definition} />
						</div>
					</AccordionContent>
				</AccordionItem>
			{/each}
		</Accordion>
	</div>
</Card>
