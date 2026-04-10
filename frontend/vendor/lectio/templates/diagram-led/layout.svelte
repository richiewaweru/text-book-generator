<script lang="ts">
	import {
		CalloutBlock,
		DiagramSeries,
		ExplanationBlock,
		GlossaryRail,
		HookHero,
		PitfallAlert,
		PracticeStack,
		ProcessSteps,
		SummaryBlock,
		WhatNextBridge
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	{#if section.diagram_series}
		<DiagramSeries content={section.diagram_series} />
	{/if}
	{#if section.callout}
		<CalloutBlock content={section.callout} />
	{/if}
	<div class="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
		<ExplanationBlock content={section.explanation} />
		{#if section.process}
			<ProcessSteps content={section.process} mode="step-reveal" />
		{/if}
	</div>
	{#if section.glossary}
		<GlossaryRail content={section.glossary} mode="inline-strip" />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="accordion" />
	{#if section.summary}
		<SummaryBlock content={section.summary} />
	{/if}
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
