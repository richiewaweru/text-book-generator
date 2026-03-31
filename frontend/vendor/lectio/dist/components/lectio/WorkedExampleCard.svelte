<script lang="ts">
	import type { WorkedExampleContent, WorkedStep } from '../../types';
	import { Card } from '../ui/card';
	import { Badge } from '../ui/badge';
	import { Button } from '../ui/button';
	import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../ui/collapsible';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent
	} from '../ui/accordion';
	import MathFormula from './MathFormula.svelte';

	let {
		content,
		mode = 'step-reveal'
	}: {
		content: WorkedExampleContent;
		mode?: 'static' | 'step-reveal' | 'accordion';
	} = $props();

	let revealed = $state(0);

	const visibleSteps = $derived(
		mode === 'step-reveal' ? content.steps.slice(0, revealed) : content.steps
	);
	const isComplete = $derived(
		mode !== 'step-reveal' || content.steps.length === 0 || revealed >= content.steps.length
	);

	$effect(() => {
		revealed = mode === 'step-reveal' ? Math.min(1, content.steps.length) : content.steps.length;
	});

	function showNextStep() {
		revealed = Math.min(content.steps.length, revealed + 1);
	}
</script>

{#snippet stepBlock(step: WorkedStep, index: number)}
	<div class="flex gap-4">
		<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-700">
			{index + 1}
		</div>
		<div class="space-y-2">
			<p class="text-sm font-semibold uppercase tracking-[0.18em] text-violet-700">
				{step.label}
			</p>
			<p class="text-base leading-7 text-foreground/85">{step.content}</p>
			{#if step.formula}
				<div class="rounded-[1rem] bg-white/85 p-3 text-primary">
					<MathFormula formula={step.formula} displayMode />
				</div>
			{/if}
			{#if step.note}
				<p class="text-sm italic leading-6 text-muted-foreground">Note: {step.note}</p>
			{/if}
			{#if step.diagram_ref}
				<p class="text-xs font-semibold uppercase tracking-[0.16em] text-violet-700/75">
					Diagram reference: {step.diagram_ref}
				</p>
			{/if}
		</div>
	</div>
{/snippet}

{#snippet methodPreview(example: WorkedExampleContent)}
	<div class="space-y-4 rounded-[1.25rem] bg-white/85 p-4">
		{#if example.method_label}
			<Badge variant="outline" class="border-violet-200 text-violet-700">
				{example.method_label}
			</Badge>
		{/if}
		<p class="text-sm leading-6 text-muted-foreground">{example.setup}</p>
		<div class="space-y-4">
			{#each example.steps as step, index}
				{@render stepBlock(step, index)}
			{/each}
		</div>
		<div class="rounded-[1rem] bg-violet-50 p-4 text-sm font-semibold leading-6 text-violet-950">
			{example.conclusion}
		</div>
	</div>
{/snippet}

<Card class="border-l-4 border-l-violet-500 bg-violet-50/45">
	<div class="space-y-5 p-6">
		<div class="space-y-3">
			<div class="flex flex-wrap items-center gap-3">
				<p class="eyebrow text-violet-600">Example</p>
				{#if content.method_label}
					<Badge variant="outline" class="border-violet-200 text-violet-700">
						{content.method_label}
					</Badge>
				{/if}
			</div>
			<h3 class="text-2xl font-semibold font-serif text-primary">{content.title}</h3>
			<p class="text-sm leading-6 text-muted-foreground">{content.setup}</p>
		</div>

		{#if mode === 'accordion'}
			<Accordion type="single" class="space-y-3">
				{#each content.steps as step, index}
					<AccordionItem value={`step-${index}`} class="bg-white/70">
						<AccordionTrigger>
							<span class="flex items-center gap-3">
								<span class="flex h-7 w-7 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
									{index + 1}
								</span>
								{step.label}
							</span>
						</AccordionTrigger>
						<AccordionContent class="space-y-3">
							{@render stepBlock(step, index)}
						</AccordionContent>
					</AccordionItem>
				{/each}
			</Accordion>
		{:else}
			<div class="space-y-4">
				{#each visibleSteps as step, index}
					<div class="animate-step-reveal">
						{@render stepBlock(step, index)}
					</div>
				{/each}
			</div>
		{/if}

		{#if mode === 'step-reveal' && revealed < content.steps.length}
			<Button variant="outline" class="w-fit" onclick={showNextStep}>
				Show next step
			</Button>
		{/if}

		<div class="rounded-[1.25rem] bg-white/85 p-4 text-sm font-semibold leading-7 text-primary">
			{content.conclusion}
		</div>

		{#if isComplete && content.answer}
			<div class="rounded-[1.25rem] bg-violet-100 p-4 text-sm leading-7 text-violet-950">
				<span class="mr-2 font-semibold uppercase tracking-[0.18em] text-violet-700">Answer:</span>
				{content.answer}
			</div>
		{/if}

		{#if isComplete && content.alternative}
			<Collapsible>
				<CollapsibleTrigger
					class="inline-flex h-9 items-center justify-center rounded-xl px-0 text-sm font-medium text-violet-700 transition-colors hover:text-violet-800"
				>
					Alternative method
				</CollapsibleTrigger>
				<CollapsibleContent class="pt-2">
					{@render methodPreview(content.alternative)}
				</CollapsibleContent>
			</Collapsible>
		{/if}

		{#if isComplete && content.alternatives?.length}
			<Collapsible>
				<CollapsibleTrigger
					class="inline-flex h-9 items-center justify-center rounded-xl px-0 text-sm font-medium text-violet-700 transition-colors hover:text-violet-800"
				>
					Other approaches
				</CollapsibleTrigger>
				<CollapsibleContent class="rounded-[1.25rem] bg-white/80 p-4 text-sm leading-6 text-foreground/82">
					<ul class="list-disc space-y-2 pl-5">
						{#each content.alternatives as alternative}
							<li>{alternative}</li>
						{/each}
					</ul>
				</CollapsibleContent>
			</Collapsible>
		{/if}
	</div>
</Card>
