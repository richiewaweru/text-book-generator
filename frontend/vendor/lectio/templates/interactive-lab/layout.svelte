<script lang="ts">
	import {
		DefinitionCard,
		DiagramBlock,
		ExplanationBlock,
		HookHero,
		PitfallAlert,
		PracticeStack,
		SimulationBlock,
		WhatNextBridge,
		WorkedExampleCard
	} from '../../components/lectio';
	import { getSectionSimulations } from '../../section-content';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
	const simulations = $derived(getSectionSimulations(section));
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	{#each simulations as simulation}
		<SimulationBlock content={simulation} />
	{/each}
	<ExplanationBlock content={section.explanation} />
	{#if section.definition}
		<DefinitionCard content={section.definition} />
	{/if}
	{#if section.diagram}
		<DiagramBlock content={section.diagram} />
	{/if}
	{#if section.worked_example}
		<WorkedExampleCard content={section.worked_example} />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="accordion" />
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
