<script lang="ts">
	import type { DiagramSeriesContent } from '../../types';
	import { Card } from '../ui/card';
	import { Button } from '../ui/button';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';

let { content }: { content: DiagramSeriesContent } = $props();

let current = $state(0);

const activeDiagram = $derived(content.diagrams[current] ?? content.diagrams[0]);

$effect(() => {
	current = content.diagrams.length === 0 ? 0 : Math.min(current, content.diagrams.length - 1);
});

const progressPercent = $derived(
	!activeDiagram || content.diagrams.length <= 1
		? 100
		: ((current + 1) / content.diagrams.length) * 100
);
</script>

<Card class="border-primary/10 bg-white/88 p-6">
	<div class="space-y-5">
		<div class="space-y-2">
			<p class="eyebrow">Series</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.title}</h3>
		</div>

		{#if activeDiagram}
			<div class="space-y-3 rounded-[1.2rem] border border-border/70 bg-white/78 p-4">
				<div class="flex items-center justify-between gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
					<span>Step {current + 1} of {content.diagrams.length}</span>
					<span>{activeDiagram.step_label}</span>
				</div>

				<div
					class="grid gap-2"
					style="grid-template-columns: repeat({content.diagrams.length}, minmax(0, 1fr));"
				>
					{#each content.diagrams as diagram, index}
						<button
							type="button"
							onclick={() => (current = index)}
							class="group rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
							aria-current={index === current ? 'step' : undefined}
							aria-label={`Go to ${diagram.step_label}`}
						>
							<span
								class="block h-2 rounded-full transition-all {index <= current
									? 'bg-primary'
									: 'bg-secondary group-hover:bg-secondary/80'}"
							></span>
						</button>
					{/each}
				</div>

				<div class="h-1.5 overflow-hidden rounded-full bg-secondary">
					<div
						class="h-full rounded-full bg-gradient-to-r from-primary to-accent transition-all"
						style="width: {progressPercent}%"
					></div>
				</div>

				<div class="flex flex-wrap items-center justify-between gap-3">
					<Button
						size="sm"
						variant="outline"
						onclick={() => (current = Math.max(0, current - 1))}
						disabled={current === 0}
					>
						<ChevronLeft class="h-4 w-4" />
						Previous
					</Button>

					<div class="flex flex-wrap gap-2">
						{#each content.diagrams as diagram, index}
							<Button
								size="sm"
								variant={index === current ? 'default' : 'outline'}
								class="text-xs"
								onclick={() => (current = index)}
							>
								{diagram.step_label}
							</Button>
						{/each}
					</div>

					<Button
						size="sm"
						variant="outline"
						onclick={() => (current = Math.min(content.diagrams.length - 1, current + 1))}
						disabled={current === content.diagrams.length - 1}
					>
						Next
						<ChevronRight class="h-4 w-4" />
					</Button>
				</div>
			</div>

			<div class="overflow-hidden rounded-[1.25rem] border border-border/70 bg-white [&_svg]:h-auto [&_svg]:w-full">
				{@html activeDiagram.svg_content}
			</div>

			<p class="text-sm leading-6 text-muted-foreground">{activeDiagram.caption}</p>
		{/if}
	</div>
</Card>
