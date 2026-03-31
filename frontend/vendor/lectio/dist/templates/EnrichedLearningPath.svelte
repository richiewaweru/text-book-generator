<script lang="ts">
	import type { SectionContent } from '../types';
	import { validateSection, warnIfInvalid } from '../validate';
	import {
		SectionHeader,
		PrerequisiteStrip,
		HookHero,
		ExplanationBlock,
		InsightStrip,
		DefinitionCard,
		DefinitionFamily,
		DiagramBlock,
		WorkedExampleCard,
		ProcessSteps,
		DiagramCompare,
		DiagramSeries,
		PitfallAlert,
		QuizCheck,
		PracticeStack,
		ReflectionPrompt,
		SimulationBlock,
		InterviewAnchor,
		WhatNextBridge,
		GlossaryRail,
		GlossaryInline
	} from '../components/lectio';
	import { Card } from '../components/ui/card';
	import { AlertTriangle } from 'lucide-svelte';

	let { section }: { section: SectionContent } = $props();

	let warnings = $state<string[]>([]);
	const inlineTerm = $derived(section.glossary?.terms[0] ?? null);

	$effect(() => {
		warnings = validateSection(section);
		warnIfInvalid(section);
	});
</script>

<div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
	<div class="lesson-shell p-6 sm:p-8">
		<div class="relative z-10 space-y-6">
			<SectionHeader content={section.header} />

			{#if warnings.length > 0}
				<Card class="border-amber-300 bg-amber-50/92 p-4">
					<div class="flex gap-3">
						<AlertTriangle class="mt-1 h-5 w-5 shrink-0 text-amber-700" />
						<div>
							<p class="font-semibold text-amber-900">Schema capacity warnings</p>
							<ul class="mt-2 space-y-1 text-sm text-amber-950/80">
								{#each warnings as warning}
									<li>{warning}</li>
								{/each}
							</ul>
						</div>
					</div>
				</Card>
			{/if}

			{#if section.prerequisites}
				<PrerequisiteStrip content={section.prerequisites} />
			{/if}

			<HookHero content={section.hook} />
			<ExplanationBlock content={section.explanation} />

			{#if inlineTerm}
				<div class="rounded-[1.35rem] border border-border/70 bg-white/82 p-4 text-sm leading-7 text-foreground/84">
					Inline term preview:
					<GlossaryInline term={inlineTerm.term} definition={inlineTerm.definition} />
					can sit inside narrative text without pulling the learner away from the main
					explanation.
				</div>
			{/if}

			{#if section.insight_strip}
				<InsightStrip content={section.insight_strip} />
			{/if}

			{#if section.definition_family}
				<DefinitionFamily content={section.definition_family} />
			{:else if section.definition}
				<DefinitionCard content={section.definition} />
			{/if}

			{#if section.diagram}
				<DiagramBlock content={section.diagram} />
			{/if}

			{#if section.worked_example}
				<WorkedExampleCard content={section.worked_example} mode="step-reveal" />
			{/if}

			{#if section.worked_examples}
				<div class="space-y-5">
					{#each section.worked_examples as ex, index}
						<WorkedExampleCard
							content={ex}
							mode={index === 0 ? 'step-reveal' : 'accordion'}
						/>
					{/each}
				</div>
			{/if}

			{#if section.process}
				<ProcessSteps content={section.process} />
			{/if}

			{#if section.diagram_compare}
				<DiagramCompare content={section.diagram_compare} />
			{/if}

			{#if section.diagram_series}
				<DiagramSeries content={section.diagram_series} />
			{/if}

			{#if section.pitfall}
				<PitfallAlert content={section.pitfall} />
			{/if}

			{#if section.pitfalls}
				<div class="space-y-4">
					{#each section.pitfalls as pitfall}
						<PitfallAlert content={pitfall} />
					{/each}
				</div>
			{/if}

			{#if section.quiz}
				<QuizCheck content={section.quiz} />
			{/if}

			<PracticeStack content={section.practice} />

			{#if section.reflection}
				<ReflectionPrompt content={section.reflection} />
			{/if}

			{#if section.simulation}
				<SimulationBlock content={section.simulation} />
			{/if}

			{#if section.interview}
				<InterviewAnchor content={section.interview} />
			{/if}

			<WhatNextBridge content={section.what_next} />
		</div>
	</div>

	{#if section.glossary}
		<aside class="xl:sticky xl:top-8 xl:self-start">
			<GlossaryRail content={section.glossary} />
		</aside>
	{/if}
</div>
