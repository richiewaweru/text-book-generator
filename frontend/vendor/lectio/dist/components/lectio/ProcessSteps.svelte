<script lang="ts">
	import type { ProcessContent } from '../../types';
	import { Button } from '../ui/button';
	import { Card } from '../ui/card';

	let {
		content,
		mode = 'static'
	}: { content: ProcessContent; mode?: 'static' | 'step-reveal' } = $props();

	let visibleSteps = $state(0);

	$effect(() => {
		visibleSteps = mode === 'step-reveal' ? Math.min(1, content.steps.length) : content.steps.length;
	});

	const renderedSteps = $derived(
		mode === 'step-reveal' ? content.steps.slice(0, visibleSteps) : content.steps
	);

	function formatInputOutput(step: ProcessContent['steps'][number]) {
		const pieces: string[] = [];

		if (step.input) {
			pieces.push(`Input: ${step.input}`);
		}

		if (step.output) {
			pieces.push(`Output: ${step.output}`);
		}

		return pieces.join('  ');
	}
</script>

<Card class="border-emerald-200 bg-emerald-50/45 p-6">
	<div class="space-y-4">
		<div class="space-y-2">
			<p class="eyebrow text-emerald-700">Process</p>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.title}</h3>
			{#if content.intro}
				<p class="text-sm leading-6 text-muted-foreground">{content.intro}</p>
			{/if}
		</div>

		{#each renderedSteps as step}
			<div class="rounded-[1.25rem] border border-emerald-100 bg-white/82 p-4">
				<div class="flex items-start gap-4">
					<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700">
						{step.number}
					</div>
					<div class="space-y-2">
						<p class="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">
							{step.action}
						</p>
						<p class="text-base leading-7 text-foreground/84">{step.detail}</p>
						{#if step.input || step.output}
							<p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">
								{formatInputOutput(step)}
							</p>
						{/if}
						{#if step.warning}
							<p class="text-sm italic leading-6 text-amber-800">Watch for: {step.warning}</p>
						{/if}
					</div>
				</div>
			</div>
		{/each}

		{#if mode === 'step-reveal' && visibleSteps < content.steps.length}
			<Button
				variant="outline"
				onclick={() => (visibleSteps = Math.min(visibleSteps + 1, content.steps.length))}
			>
				Show next step
			</Button>
		{/if}
	</div>
</Card>
