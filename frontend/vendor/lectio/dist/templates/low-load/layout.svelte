<script lang="ts">
	import {
		DefinitionCard,
		ExplanationBlock,
		GlossaryInline,
		HookHero,
		PitfallAlert,
		PracticeStack,
		ReflectionPrompt,
		WhatNextBridge
	} from '../../components/lectio';
	import type { SectionContent } from '../../types';

	import TemplateShell from '../TemplateShell.svelte';

	let { section }: { section: SectionContent } = $props();

	const inlineTerm = $derived(section.glossary?.terms[0]);
</script>

<TemplateShell {section} singleColumn contentClassName="space-y-8">
	<HookHero content={section.hook} />
	<ExplanationBlock content={section.explanation} />
	{#if inlineTerm}
		<div class="rounded-[1.25rem] border border-border/70 bg-white/88 p-4 text-sm leading-7 text-foreground/84">
			Focus cue: if you forget the term
			<GlossaryInline term={inlineTerm.term} definition={inlineTerm.definition} />
			, open it in place and keep reading.
		</div>
	{/if}
	{#if section.definition}
		<DefinitionCard content={section.definition} />
	{/if}
	{#if section.pitfall}
		<PitfallAlert content={section.pitfall} />
	{/if}
	<PracticeStack content={section.practice} mode="flat-list" />
	{#if section.reflection}
		<ReflectionPrompt content={section.reflection} />
	{/if}
	<WhatNextBridge content={section.what_next} />
</TemplateShell>
