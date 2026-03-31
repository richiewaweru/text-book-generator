<script lang="ts">
	import {
		ExplanationBlock,
		HookHero,
		PitfallAlert,
		PracticeStack,
		ReflectionPrompt,
		TimelineBlock,
		WhatNextBridge
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();
</script>

<TemplateShell {section} singleColumn>
	<HookHero content={section.hook} />
	{#if section.timeline}
		<TimelineBlock content={section.timeline} mode="timeline-scrubber" />
	{/if}
	<ExplanationBlock content={section.explanation} />
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	{#if section.reflection}
		<ReflectionPrompt content={section.reflection} />
	{/if}
	<PracticeStack content={section.practice} mode="accordion" />
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
