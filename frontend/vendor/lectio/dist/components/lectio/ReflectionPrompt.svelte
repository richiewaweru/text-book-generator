<script lang="ts">
	import type { ReflectionContent } from '../../types';
	import { Card } from '../ui/card';
	import { Brain } from 'lucide-svelte';

	let { content }: { content: ReflectionContent } = $props();

	const typeLabels: Record<string, string> = {
		open: 'Reflect',
		'pair-share': 'Pair and share',
		'sentence-stem': 'Complete the thought',
		timed: 'Timed reflection',
		connect: 'Make a connection',
		predict: 'Predict',
		transfer: 'Transfer'
	};
</script>

<Card class="border-l-4 border-l-indigo-400 bg-indigo-50/50 p-6">
	<div class="flex gap-3">
		<Brain class="mt-0.5 h-5 w-5 shrink-0 text-indigo-500" />
		<div class="flex-1 space-y-3">
			<div class="space-y-2">
				<p class="eyebrow text-indigo-600">{typeLabels[content.type] ?? 'Reflect'}</p>
				<p class="text-sm leading-7 text-foreground">{content.prompt}</p>
			</div>

			{#if content.type === 'sentence-stem' && content.sentence_stem}
				<p class="rounded-xl bg-white/60 p-3 text-sm italic text-indigo-600/80">
					{content.sentence_stem}
				</p>
			{/if}

			{#if content.type === 'timed' && content.time_minutes}
				<p class="text-xs text-muted-foreground">
					Take {content.time_minutes} minute{content.time_minutes > 1 ? 's' : ''} to think about
					this.
				</p>
			{/if}

			{#if content.type === 'pair-share' && content.pair_instruction}
				<p class="text-xs font-medium italic text-indigo-600">{content.pair_instruction}</p>
			{/if}

			{#if content.space && content.space > 0}
				<div class="print-only mt-3 space-y-3">
					{#each Array.from({ length: content.space }) as _}
						<div class="h-8 border-b border-indigo-200"></div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Card>
