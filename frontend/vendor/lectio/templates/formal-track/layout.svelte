<script lang="ts">
	import {
		DefinitionCard,
		ExplanationBlock,
		HookHero,
		PitfallAlert,
		PracticeStack,
		WhatNextBridge,
		WorkedExampleCard
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	<ExplanationBlock content={section.explanation} />
	{#if section.definition}
		<DefinitionCard content={section.definition} />
	{/if}
	{#if section.worked_example}
		<WorkedExampleCard content={section.worked_example} mode="static" />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="flat-list" />
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
