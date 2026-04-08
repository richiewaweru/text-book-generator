<script lang="ts">
	import type { SectionContent } from '../types';
	import { validateSection, warnIfInvalid } from '../validate';
	import {
		SectionHeader,
		HookHero,
		ExplanationBlock,
		DefinitionCard,
		WorkedExampleCard,
		PracticeStack,
		PitfallAlert,
		GlossaryRail,
		WhatNextBridge
	} from '../components/lectio';
	import { Card } from '../components/ui/card';
	import { AlertTriangle } from 'lucide-svelte';

	let { section }: { section: SectionContent } = $props();

	let warnings = $state<string[]>([]);

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

			<HookHero content={section.hook} />
			<ExplanationBlock content={section.explanation} />

			{#if section.definition}
				<DefinitionCard content={section.definition} />
			{/if}

			{#if section.worked_example}
				<WorkedExampleCard content={section.worked_example} mode="step-reveal" />
			{/if}

			{#if section.pitfall}
				<PitfallAlert content={section.pitfall} />
			{/if}

			<PracticeStack content={section.practice} />
			<WhatNextBridge content={section.what_next} />
		</div>
	</div>

	{#if section.glossary}
		<aside class="xl:sticky xl:top-8 xl:self-start">
			<GlossaryRail content={section.glossary} />
		</aside>
	{/if}
</div>
