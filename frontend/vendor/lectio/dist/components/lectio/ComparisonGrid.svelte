<script lang="ts">
	import type { ComparisonGridContent } from '../../types';
	import { Badge } from '../ui/badge';
	import { Card } from '../ui/card';

	let { content }: { content: ComparisonGridContent } = $props();

	const gridTemplate = $derived(
		`grid-template-columns: minmax(9rem, 1.1fr) repeat(${content.columns.length}, minmax(10rem, 1fr));`
	);
</script>

<Card class="border-cyan-200 bg-cyan-50/45 p-6">
	<div class="space-y-5">
		<div class="space-y-2">
			<p class="eyebrow text-cyan-700">Comparison</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.title}</h3>
			{#if content.intro}
				<p class="text-sm leading-6 text-muted-foreground">{content.intro}</p>
			{/if}
		</div>

		<div class="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
			{#each content.columns as column}
				<div
					class={`rounded-[1.25rem] border bg-white/82 p-4 ${
						column.highlight
							? 'border-cyan-300 shadow-[0_12px_30px_rgba(8,145,178,0.12)]'
							: 'border-cyan-100'
					}`}
				>
					<div class="flex items-center gap-2">
						<p class="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-700">
							{column.title}
						</p>
						{#if column.badge}
							<Badge variant="outline" class="border-cyan-200 text-cyan-700">
								{column.badge}
							</Badge>
						{/if}
					</div>
					<p class="mt-3 text-base leading-7 text-foreground/84">{column.summary}</p>
					{#if column.detail}
						<p class="mt-2 text-sm leading-6 text-muted-foreground">{column.detail}</p>
					{/if}
				</div>
			{/each}
		</div>

		<div class="overflow-x-auto rounded-[1.25rem] border border-cyan-100 bg-white/88">
			<div class="min-w-[48rem]">
				<div class="grid items-stretch border-b border-cyan-100 bg-cyan-50/80" style={gridTemplate}>
					<div class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
						Criterion
					</div>
					{#each content.columns as column}
						<div class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
							{column.title}
						</div>
					{/each}
				</div>

				{#each content.rows as row}
					<div class="grid border-t border-cyan-100 first:border-t-0" style={gridTemplate}>
						<div class="px-4 py-4 text-sm font-semibold text-primary">
							{row.criterion}
							{#if row.takeaway}
								<p class="mt-1 text-xs font-normal uppercase tracking-[0.16em] text-muted-foreground">
									{row.takeaway}
								</p>
							{/if}
						</div>
						{#each row.values as value}
							<div class="px-4 py-4 text-sm leading-6 text-foreground/82">{value}</div>
						{/each}
					</div>
				{/each}
			</div>
		</div>

		{#if content.apply_prompt}
			<div class="rounded-[1.15rem] bg-cyan-100/70 p-4 text-sm leading-6 text-cyan-950">
				<span class="mr-2 font-semibold uppercase tracking-[0.18em] text-cyan-700">
					Apply it
				</span>
				{content.apply_prompt}
			</div>
		{/if}
	</div>
</Card>
