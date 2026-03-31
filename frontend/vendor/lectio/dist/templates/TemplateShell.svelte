<script lang="ts">
	import type { Snippet } from 'svelte';

	import { SectionHeader } from '../components/lectio';
	import { cn } from '../utils';
	import type { SectionContent } from '../types';

	import TemplateWarnings from './TemplateWarnings.svelte';

	let {
		section,
		children,
		sidebar,
		singleColumn = false,
		contentClassName
	}: {
		section: SectionContent;
		children: Snippet;
		sidebar?: Snippet;
		singleColumn?: boolean;
		contentClassName?: string;
	} = $props();
</script>

{#if singleColumn || !sidebar}
	<div class="lesson-shell p-6 sm:p-8">
		<div class={cn('relative z-10 space-y-6', contentClassName)}>
			<SectionHeader content={section.header} />
			<TemplateWarnings {section} />
			{@render children()}
		</div>
	</div>
{:else}
	<div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
		<div class="lesson-shell p-6 sm:p-8">
			<div class={cn('relative z-10 space-y-6', contentClassName)}>
				<SectionHeader content={section.header} />
				<TemplateWarnings {section} />
				{@render children()}
			</div>
		</div>
		<aside class="xl:sticky xl:top-8 xl:self-start">
			{@render sidebar()}
		</aside>
	</div>
{/if}
