<script lang="ts">
	import {
		DefinitionCard,
		DiagramBlock,
		ExplanationBlock,
		GlossaryRail,
		HookHero,
		PitfallAlert,
		PracticeStack,
		ReflectionPrompt,
		SimulationBlock,
		WhatNextBridge,
		WorkedExampleCard
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section}>
	{#snippet sidebar()}
		{#if section.glossary}
			<GlossaryRail content={section.glossary} mode="sticky" />
		{/if}
	{/snippet}

	<HookHero content={section.hook} />
	<ExplanationBlock content={section.explanation} />
	{#if section.definition}
		<DefinitionCard content={section.definition} />
	{/if}
	{#if section.diagram}
		<DiagramBlock content={section.diagram} />
	{/if}
	{#if section.simulation}
		<SimulationBlock content={section.simulation} />
	{/if}
	{#if section.worked_example}
		<WorkedExampleCard content={section.worked_example} mode="step-reveal" />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="accordion" />
	{#if section.reflection}
		<ReflectionPrompt content={section.reflection} />
	{/if}
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
