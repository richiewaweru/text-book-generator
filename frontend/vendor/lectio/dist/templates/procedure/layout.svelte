<script lang="ts">
	import {
		ExplanationBlock,
		HookHero,
		PitfallAlert,
		PracticeStack,
		ProcessSteps,
		WhatNextBridge,
		WorkedExampleCard
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	{#if section.process}
		<ProcessSteps content={section.process} mode="step-reveal" />
	{/if}
	<ExplanationBlock content={section.explanation} />
	{#if section.worked_example}
		<WorkedExampleCard content={section.worked_example} mode="static" />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="flat-list" />
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
