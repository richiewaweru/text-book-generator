<script lang="ts">
	import {
		ComparisonGrid,
		DefinitionFamily,
		ExplanationBlock,
		HookHero,
		InsightStrip,
		PitfallAlert,
		PracticeStack,
		WhatNextBridge
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	<ExplanationBlock content={section.explanation} />
	{#if section.definition_family}
		<DefinitionFamily content={section.definition_family} />
	{/if}
	{#if section.insight_strip}
		<InsightStrip content={section.insight_strip} />
	{/if}
	{#if section.comparison_grid}
		<ComparisonGrid content={section.comparison_grid} />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="flat-list" />
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
